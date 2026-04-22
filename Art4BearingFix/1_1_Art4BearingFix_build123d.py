"""
1_1_Art4BearingFix_build123d.py

Clean rewrite: Pure face assembly -> Sew -> Solid -> Cut holes -> Export.
  G1: Base flat outline (S1) -> Bottom Face.
  G2: Top curved surface (S2) + Hole fills (S3, S4) -> Top Faces & Caps.
  G3: Side walls (S5) -> Side Faces.
  G4: Sew all faces, log free edges (Watertight check), make Solid.
  G5: Export to STL.
  G6: Read S6 — two polygon-circle profiles at Z=0.
  G7: Extrude-cut both S6 profiles by 4 units in +Z.
  G8: Read S7 — two polygon-circle profiles at Z=1.
  G9: Extrude-cut both S7 profiles by 4 units in +Z.

  NOTE: Circles are kept as line-segment polygons from CSV data.
        We do NOT fit center/radius — that would deviate from original mesh.
"""

import os
import csv
import math
from build123d import *
from ocp_vscode import show, set_port

# ── PATHS & CONFIG ──
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/1_Art4BearingFix"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

SCRIPT_STEM = "1_Art4BearingFix_build123d"
G_RANGE     = "1_9"
STL_NAME    = f"{SCRIPT_STEM}_G_{G_RANGE}.stl"
LOG_NAME    = f"{SCRIPT_STEM}_summary_G_{G_RANGE}.txt"

HOLE_CUT_DEPTH = 4  # +Z extrude-cut for G7 and G9

# ══════════════════════════════════════════════════════════════
# DATA PARSING
# ══════════════════════════════════════════════════════════════
def read_csv(filename):
    filepath = os.path.join(CSV_DIR, filename)
    if not os.path.exists(filepath):
        print(f"⚠️ Warning: {filename} not found.")
        return []

    rows = []
    with open(filepath, "r") as f:
        for row in csv.DictReader(f):
            parsed = {
                "draw_type": row["Draw Type"].strip().lower(),
                "p1": (float(row["X1"]), float(row["Y1"]), float(row["Z1"])),
                "p2": None, "p3": None
            }
            if row["X2"].strip() != "NA":
                parsed["p2"] = (float(row["X2"]), float(row["Y2"]), float(row["Z2"]))
            if row["X3"].strip() != "NA":
                parsed["p3"] = (float(row["X3"]), float(row["Y3"]), float(row["Z3"]))
            rows.append(parsed)
    return rows

# ══════════════════════════════════════════════════════════════
# GEOMETRY HELPERS (OCP)
# ══════════════════════════════════════════════════════════════
def make_triangle_face(p1, p2, p3):
    """Creates a 3D triangle face from 3 points."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt
    poly = BRepBuilderAPI_MakePolygon(gp_Pnt(*p1), gp_Pnt(*p2), gp_Pnt(*p3), True)
    face_maker = BRepBuilderAPI_MakeFace(poly.Wire())
    return face_maker.Face() if face_maker.IsDone() else None

def order_points(rows):
    """Snaps unordered line segments into a continuous point loop."""
    segs = [(r["p1"], r["p2"]) for r in rows if r["draw_type"] == "line" and r["p2"] is not None]
    if not segs: return []

    ordered = [segs[0][0], segs[0][1]]
    used = {0}
    tolerance = 1e-3

    def pts_close(a, b): return math.hypot(a[0]-b[0], a[1]-b[1]) < tolerance

    for _ in range(len(segs)):
        added = False
        for i, (p1, p2) in enumerate(segs):
            if i in used: continue
            if pts_close(ordered[-1], p1):
                ordered.append(p2); used.add(i); added = True; break
            elif pts_close(ordered[-1], p2):
                ordered.append(p1); used.add(i); added = True; break
        if not added: break

    if len(ordered) > 2 and pts_close(ordered[0], ordered[-1]):
        ordered.pop()

    return ordered

def fan_triangulate(pts):
    """Fills a point loop with fan triangulation from the centroid."""
    if len(pts) < 3: return []
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    cz = sum(p[2] for p in pts) / len(pts)
    center = (cx, cy, cz)

    faces = []
    n = len(pts)
    for i in range(n):
        f = make_triangle_face(pts[i], pts[(i+1)%n], center)
        if f: faces.append(f)
    return faces

def make_polygon_prism(points, z_val, height, label):
    """Build a polygon wire → face → prism at given Z, extruded by height in +Z.
       Uses line segments directly — no center/radius fitting."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Pnt, gp_Vec

    wire_maker = BRepBuilderAPI_MakeWire()
    for i in range(len(points)):
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        edge = BRepBuilderAPI_MakeEdge(
            gp_Pnt(p1[0], p1[1], z_val),
            gp_Pnt(p2[0], p2[1], z_val)
        ).Edge()
        wire_maker.Add(edge)

    if not wire_maker.IsDone():
        print(f"   ❌ Wire failed for {label}")
        return None

    face_maker = BRepBuilderAPI_MakeFace(wire_maker.Wire())
    if not face_maker.IsDone():
        print(f"   ❌ Face failed for {label}")
        return None

    prism = BRepPrimAPI_MakePrism(face_maker.Face(), gp_Vec(0, 0, height))
    if prism.IsDone():
        print(f"   ✓ Prism built for {label}")
        return prism.Shape()

    print(f"   ❌ Prism failed for {label}")
    return None

def cut_solid_with_prism(current_solid, prism, label):
    """Subtract a prism from a solid using BRepAlgoAPI_Cut with fuzzy tolerance."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape

    cutter = BRepAlgoAPI_Cut()
    args = TopTools_ListOfShape()
    args.Append(current_solid)
    cutter.SetArguments(args)
    tools = TopTools_ListOfShape()
    tools.Append(prism)
    cutter.SetTools(tools)
    cutter.SetFuzzyValue(1e-3)
    cutter.Build()

    if cutter.IsDone():
        print(f"   ✓ Cut {label} from body.")
        return cutter.Shape()
    else:
        print(f"   ❌ Cut {label} failed.")
        return current_solid

def split_circles_by_x(rows):
    """Split S6/S7 rows into two groups by X sign (circle 1: X>0, circle 2: X<0)."""
    pos_rows = [r for r in rows if r["p1"][0] > 0]
    neg_rows = [r for r in rows if r["p1"][0] < 0]
    return pos_rows, neg_rows

def extract_largest_solid(shape):
    """Extract the largest solid by volume from a shape."""
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer

    solids = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solids.append(Solid(explorer.Current()))
        explorer.Next()

    if not solids:
        return None

    def get_vol(s):
        v = s.volume
        return v() if callable(v) else v

    best = max(solids, key=get_vol)
    print(f"   ℹ️ {len(solids)} solid(s). Largest volume = {get_vol(best):.3f}")
    return best

# ══════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════
def main():
    log_lines = []
    def log(msg):
        print(msg)
        log_lines.append(msg)

    log("=" * 50)
    log("  ASSEMBLING WATERTIGHT MESH")
    log("=" * 50)

    all_faces = []

    # ── G1: Bottom Face (S1) ──
    log("-> [G1] Building bottom face (S1)...")
    s1_pts = order_points(read_csv("Fusion_Coordinates_S1.csv"))
    if s1_pts:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
        from OCP.gp import gp_Pnt

        poly = BRepBuilderAPI_MakePolygon()
        for pt in s1_pts:
            poly.Add(gp_Pnt(*pt))
        poly.Close()

        face_maker = BRepBuilderAPI_MakeFace(poly.Wire())
        if face_maker.IsDone():
            all_faces.append(face_maker.Face())
            log(f"   ✓ Bottom face created from {len(s1_pts)} segments.")
        else:
            log("   ❌ Failed to generate bottom face geometry.")

    # ── G2: Top Surface (S2) & Hole Caps (S3, S4) ──
    log("-> [G2] Building top surface and hole caps...")
    s2_rows = read_csv("Fusion_Coordinates_S2.csv")
    top_count = 0
    for r in s2_rows:
        if r["draw_type"].startswith("triangular") and r["p3"] is not None:
            f = make_triangle_face(r["p1"], r["p2"], r["p3"])
            if f:
                all_faces.append(f)
                top_count += 1

    s3_faces = fan_triangulate(order_points(read_csv("Fusion_Coordinates_S3.csv")))
    all_faces.extend(s3_faces)

    s4_faces = fan_triangulate(order_points(read_csv("Fusion_Coordinates_S4.csv")))
    all_faces.extend(s4_faces)
    log(f"   ✓ {top_count} top faces + {len(s3_faces)} hole1 caps + {len(s4_faces)} hole2 caps.")

    # ── G3: Side Walls (S5) ──
    log("-> [G3] Building side walls (S5)...")
    s5_rows = read_csv("Fusion_Coordinates_S5.csv")
    side_count = 0
    for r in s5_rows:
        if r["draw_type"].startswith("triangular") and r["p3"] is not None:
            f = make_triangle_face(r["p1"], r["p2"], r["p3"])
            if f:
                all_faces.append(f)
                side_count += 1
    log(f"   ✓ {side_count} side wall faces.")

    # ── G4: Sew -> Solid ──
    log(f"\n-> [G4] Sewing {len(all_faces)} faces together...")
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    sewer = BRepBuilderAPI_Sewing(0.01)
    for f in all_faces:
        sewer.Add(f)
    sewer.Perform()

    free_edges = sewer.NbFreeEdges()
    log(f"   ► FREE EDGES: {free_edges}")
    if free_edges == 0:
        log("   🟢 SUCCESS: Mesh is 100% Watertight!")
    else:
        log(f"   🔴 WARNING: Mesh has {free_edges} free edge(s). Not watertight.")

    solid_maker = BRepBuilderAPI_MakeSolid()
    explorer = TopExp_Explorer(sewer.SewedShape(), TopAbs_SHELL)
    shell_count = 0
    while explorer.More():
        solid_maker.Add(TopoDS.Shell_s(explorer.Current()))
        shell_count += 1
        explorer.Next()

    log(f"   ℹ️ {shell_count} shell(s) found.")

    if solid_maker.IsDone():
        final_solid = Solid(solid_maker.Solid())
        vol = final_solid.volume
        vol_val = vol() if callable(vol) else vol
        log(f"   ✓ Solid created. Volume = {vol_val:.3f}")
    else:
        log("   ❌ MakeSolid failed. Using shell.")
        final_solid = Shell(sewer.SewedShape())

    log("--- [G4] Complete ✓ ---")

    # ── G5: Export STL (always last — renumbered content below) ──
    # G5 is the final export step. But first, G6-G9 modify the solid.

    # ── G6: Draw Two Circle Profiles from S6 (Z=0) ──
    log("\n-> [G6] Drawing circle profiles from S6 (Z=0)...")
    s6_rows = read_csv("Fusion_Coordinates_S6.csv")
    s6_pos, s6_neg = split_circles_by_x(s6_rows)
    circle1_pts = order_points(s6_pos)
    circle2_pts = order_points(s6_neg)
    log(f"   ✓ Circle 1: {len(circle1_pts)} pts | Circle 2: {len(circle2_pts)} pts")
    log("--- [G6] Complete ✓ ---")

    # ── G7: Extrude-Cut S6 Circles +4 in Z ──
    log(f"\n-> [G7] Extrude-cut S6 circles +{HOLE_CUT_DEPTH}mm in Z...")
    current_shape = final_solid.wrapped if isinstance(final_solid, Solid) else final_solid

    prism1 = make_polygon_prism(circle1_pts, 0.0, HOLE_CUT_DEPTH, "S6 Circle 1") if circle1_pts else None
    prism2 = make_polygon_prism(circle2_pts, 0.0, HOLE_CUT_DEPTH, "S6 Circle 2") if circle2_pts else None

    if prism1: current_shape = cut_solid_with_prism(current_shape, prism1, "S6 Circle 1")
    if prism2: current_shape = cut_solid_with_prism(current_shape, prism2, "S6 Circle 2")

    final_solid = extract_largest_solid(current_shape)
    if final_solid:
        log("--- [G7] Complete ✓ ---")
    else:
        log("   ⚠️ No solid after G7 cuts.")

    # ── G8: Draw Two Circle Profiles from S7 (Z=1) ──
    log(f"\n-> [G8] Drawing circle profiles from S7 (Z=1)...")
    s7_rows = read_csv("Fusion_Coordinates_S7.csv")
    s7_pos, s7_neg = split_circles_by_x(s7_rows)
    circle3_pts = order_points(s7_pos)
    circle4_pts = order_points(s7_neg)
    log(f"   ✓ Circle 3: {len(circle3_pts)} pts | Circle 4: {len(circle4_pts)} pts")
    log("--- [G8] Complete ✓ ---")

    # ── G9: Extrude-Cut S7 Circles +4 in Z ──
    log(f"\n-> [G9] Extrude-cut S7 circles +{HOLE_CUT_DEPTH}mm in Z...")
    current_shape = final_solid.wrapped if isinstance(final_solid, Solid) else final_solid

    prism3 = make_polygon_prism(circle3_pts, 1.0, HOLE_CUT_DEPTH, "S7 Circle 3") if circle3_pts else None
    prism4 = make_polygon_prism(circle4_pts, 1.0, HOLE_CUT_DEPTH, "S7 Circle 4") if circle4_pts else None

    if prism3: current_shape = cut_solid_with_prism(current_shape, prism3, "S7 Circle 3")
    if prism4: current_shape = cut_solid_with_prism(current_shape, prism4, "S7 Circle 4")

    final_solid = extract_largest_solid(current_shape)
    if final_solid:
        log("--- [G9] Complete ✓ ---")
    else:
        log("   ⚠️ No solid after G9 cuts.")

    # ── G5: Export STL (always at the end) ──
    log(f"\n-> [G5] Exporting to STL...")
    stl_path = os.path.join(BASE_DIR, STL_NAME)
    try:
        export_obj = final_solid if isinstance(final_solid, Solid) else Solid(final_solid)
        export_stl(export_obj, stl_path, tolerance=0.005, angular_tolerance=0.05)
        stl_size_kb = os.path.getsize(stl_path) / 1024
        log(f"   ✓ Saved: {STL_NAME} ({stl_size_kb:.1f} KB)")
        log("--- [G5] STL Export complete ✓ ---")
    except Exception as e:
        log(f"   ❌ Export failed: {e}")

    # ── Save Log ──
    log_path = os.path.join(BASE_DIR, LOG_NAME)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    print(f"\n📄 Saved summary → {LOG_NAME}")

    # ── OCP Viewer ──
    print("Displaying in OCP viewer on port 3939...")
    set_port(3939)
    if final_solid is not None:
        display_obj = final_solid if isinstance(final_solid, Solid) else Solid(final_solid)
        show([display_obj], names=["Art4BearingFix"])

if __name__ == "__main__":
    main()