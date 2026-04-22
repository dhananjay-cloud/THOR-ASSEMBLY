"""
2_1_Art4BodyBot_build123d.py

Build the Art4BodyBot part using build123d.

  G1:  Read S1 — two 3-point circle profiles at Z=4.5.
       Fit circles, build annular (ring) face.
  G2:  Extrude annular profile 4.5 units in −Z.
  G3:  Checkpoint — annular disc built.
  G4:  Read S2 — four hexagon profiles (line loops) at Z=4.5.
  G5:  Extrude-cut hexagons 2 units in −Z.
  G6:  Read S3 — four 3-point circle profiles at Z=2.5.
  G7:  Extrude-cut S3 circles 2.5 units in −Z.
  G8:  Read S4 — four 3-point circle profiles at Z=4.5.
  G9:  Extrude-cut S4 circles 4.5 units in −Z.
  G10: Read S5 — four enclosed line-segment profiles at Z=4.5.
  G11: Extrude (join) S5 profiles 10 units in +Z.
  G12: Read S6 — 32 triangular side faces + 16 lines (4 top quad pts per boss).
       Cluster into 4 boss groups. Top quad pts angle-sorted for valid polygon.
  G13: Read S7 — 8 pentagonal line loops (2 per boss), NON-PLANAR.
       Fan-triangulate each loop from its 3-D centroid.
  G14: For each boss: sew S6 tris + top quad face + 2 S7 fan-tri caps.
       Orient the closed solid (fix inverted normals).
       Boolean-cut from main body.
  G15: Read S8 — four 3-point circle profiles on individual tilted planes.
       Compute 3-D circumcircle (center, radius, plane normal) for each.
  G16: Extrude-cut each S8 circle outward-normally by 8 units.
  G17: Read S9 — four 3-point circle profiles at Z=0 (flat XY plane).
  G18: Extrude-cut S9 circles by 3 units in +Z direction.
       Watertight check before export.
  Final: Export STL + summary log.

Bug fixes in this version:
  FIX 1 — G14 INVERTED SOLID (main bug, caused cascade failure):
    After sew_faces_to_solid(), the boss solids had INWARD-pointing normals.
    Cutting the main body with an inverted solid subtracts the solid's COMPLEMENT,
    which is effectively a boolean INTERSECTION — keeping only ~130 mm³ (the boss
    prism itself) and discarding the 44000+ mm³ main body.
    Bosses B/C/D then got 'no solid after cut' because nothing remained to cut.
    FIX: BRepLib.OrientClosedSolid_s(raw_solid) called immediately after MakeSolid
    to detect and flip inverted normals to outward before the solid is used as a tool.

  FIX 2 — G12 top quad angle-sort (previous fix, kept):
    sort_pts_by_angle() ensures valid convex winding for the 4-pt polygon face.

  FIX 3 — G13 non-planar S7 (previous fix, kept):
    fan_triangulate_3d() handles S7 pentagons that span Z=6.15/7.825/14.5.
"""

import os
import csv
import math
from build123d import *
from ocp_vscode import show, set_port
from datetime import datetime

# ── PATHS & CONFIG ───────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/2_Art4BodyBot"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_RANGE   = "1_18"
STL_NAME  = f"2_Art4BodyBot_G_{G_RANGE}.stl"
LOG_NAME  = f"2_Art4BodyBot_summary_G_{G_RANGE}.txt"

EXTRUDE_DEPTH_G2  = 4.5
EXTRUDE_DEPTH_G5  = 2.0
EXTRUDE_DEPTH_G7  = 2.5
EXTRUDE_DEPTH_G9  = 4.5
EXTRUDE_DEPTH_G11 = 10.0
EXTRUDE_DEPTH_G16 = 8.0   # G16: S8 circle outward-normal cut
EXTRUDE_DEPTH_G18 = 3.0   # G18: S9 circle cut in +Z

# ════════════════════════════════════════════════════════════════════════════
# DATA PARSING
# ════════════════════════════════════════════════════════════════════════════

def read_csv(filename):
    filepath = os.path.join(CSV_DIR, filename)
    if not os.path.exists(filepath):
        print(f"⚠️  Warning: {filename} not found at {filepath}")
        return []
    rows = []
    with open(filepath, "r") as f:
        for row in csv.DictReader(f):
            parsed = {
                "draw_type": row["Draw Type"].strip().lower(),
                "p1": (float(row["X1"]), float(row["Y1"]), float(row["Z1"])),
                "p2": None, "p3": None,
            }
            if row["X2"].strip() not in ("", "NA"):
                parsed["p2"] = (float(row["X2"]), float(row["Y2"]), float(row["Z2"]))
            if row["X3"].strip() not in ("", "NA"):
                parsed["p3"] = (float(row["X3"]), float(row["Y3"]), float(row["Z3"]))
            rows.append(parsed)
    return rows

# ════════════════════════════════════════════════════════════════════════════
# GEOMETRY HELPERS
# ════════════════════════════════════════════════════════════════════════════

def circle_from_3_points(p1, p2, p3):
    ax, ay = p1[0], p1[1]; bx, by = p2[0], p2[1]; cx, cy = p3[0], p3[1]
    D = 2.0 * (ax*(by-cy) + bx*(cy-ay) + cx*(ay-by))
    if abs(D) < 1e-12:
        raise ValueError("Collinear points — cannot fit circle.")
    ux = ((ax**2+ay**2)*(by-cy) + (bx**2+by**2)*(cy-ay) + (cx**2+cy**2)*(ay-by)) / D
    uy = ((ax**2+ay**2)*(cx-bx) + (bx**2+by**2)*(ax-cx) + (cx**2+cy**2)*(bx-ax)) / D
    return (ux, uy), math.sqrt((ax-ux)**2 + (ay-uy)**2)


def circle_from_3_points_3d(p1, p2, p3):
    """
    Compute circumcircle center (3-D), radius, and plane normal from
    three NON-coplanar-in-Z points. Returns (center, radius, normal).
    The normal points outward from the origin (away from body center).
    """
    import numpy as np
    A = np.array(p1, dtype=float)
    B = np.array(p2, dtype=float)
    C = np.array(p3, dtype=float)

    # Plane normal from cross product
    AB = B - A
    AC = C - A
    normal = np.cross(AB, AC)
    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-12:
        raise ValueError("Degenerate triangle — cannot compute circle.")
    normal = normal / norm_len

    # Circumcenter via barycentric coordinates
    a2 = np.dot(B - C, B - C)
    b2 = np.dot(A - C, A - C)
    c2 = np.dot(A - B, A - B)
    cross_vec = np.cross(A - C, B - C)
    denom = 2.0 * np.dot(cross_vec, cross_vec)
    if abs(denom) < 1e-12:
        raise ValueError("Degenerate — cannot compute circumcenter.")
    wa = a2 * np.dot(A - C, A - B) / denom
    wb = b2 * np.dot(B - C, B - A) / denom
    wc = c2 * np.dot(C - A, C - B) / denom
    center = wa * A + wb * B + wc * C
    radius = np.linalg.norm(A - center)

    # Orient normal outward (away from origin)
    if np.dot(normal, center) < 0:
        normal = -normal

    return tuple(center), radius, tuple(normal)


def order_line_segments(rows):
    """Chain unordered line segments into closed loops."""
    segs = [(r["p1"], r["p2"]) for r in rows if r["draw_type"] == "line" and r["p2"]]
    if not segs: return []

    def close(a, b, tol=1e-3):
        return math.sqrt(sum((x-y)**2 for x,y in zip(a,b))) < tol

    used = set(); loops = []
    for start_idx in range(len(segs)):
        if start_idx in used: continue
        loop = [segs[start_idx][0], segs[start_idx][1]]; used.add(start_idx)
        for _ in range(len(segs)):
            added = False
            for i, (p1, p2) in enumerate(segs):
                if i in used: continue
                if close(loop[-1], p1):   loop.append(p2); used.add(i); added=True; break
                elif close(loop[-1], p2): loop.append(p1); used.add(i); added=True; break
            if not added: break
        if len(loop) > 2 and close(loop[0], loop[-1]):
            loop.pop()
        loops.append(loop)
    return loops


def sort_pts_by_angle(pts):
    """Sort 3-D points by angle around their XY centroid — ensures valid polygon winding."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return sorted(pts, key=lambda p: math.atan2(p[1]-cy, p[0]-cx))


def boss_quadrant(cx, cy):
    if   cx > 0 and cy < 0: return "A"
    elif cx > 0 and cy > 0: return "B"
    elif cx < 0 and cy > 0: return "C"
    else:                   return "D"


def make_triangle_face(p1, p2, p3):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt
    poly = BRepBuilderAPI_MakePolygon(gp_Pnt(*p1), gp_Pnt(*p2), gp_Pnt(*p3), True)
    fm = BRepBuilderAPI_MakeFace(poly.Wire())
    return fm.Face() if fm.IsDone() else None


def make_polygon_face(points):
    """Create a planar OCP face from ordered coplanar points."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge
    from OCP.gp import gp_Pnt
    wire_maker = BRepBuilderAPI_MakeWire()
    for i in range(len(points)):
        p1, p2 = points[i], points[(i+1) % len(points)]
        edge = BRepBuilderAPI_MakeEdge(gp_Pnt(*p1), gp_Pnt(*p2)).Edge()
        wire_maker.Add(edge)
    if not wire_maker.IsDone(): return None
    fm = BRepBuilderAPI_MakeFace(wire_maker.Wire())
    return fm.Face() if fm.IsDone() else None


def fan_triangulate_3d(pts):
    """
    Fan-triangulate a NON-PLANAR closed polygon from its 3-D centroid.
    Required for S7 pentagons which span Z=6.15, 7.825, 14.5.
    """
    if len(pts) < 3: return []
    cx = sum(p[0] for p in pts)/len(pts)
    cy = sum(p[1] for p in pts)/len(pts)
    cz = sum(p[2] for p in pts)/len(pts)
    centroid = (cx, cy, cz)
    faces = []
    n = len(pts)
    for i in range(n):
        f = make_triangle_face(pts[i], pts[(i+1)%n], centroid)
        if f: faces.append(f)
    return faces


def sew_faces_to_solid(faces, tol=0.01):
    """
    Sew OCP faces into a closed solid and orient normals outward.

    BRepLib.OrientClosedSolid_s() is called after MakeSolid to detect and
    correct inverted normals. Without this, face-assembled solids often have
    inward-pointing normals — using such a solid as a boolean cut tool performs
    a complement subtraction (keeps only the intersection) instead of a true cut.

    Returns (solid_or_None, free_edge_count).
    """
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.BRepLib import BRepLib  # ← FIX: normal orientation

    sewer = BRepBuilderAPI_Sewing(tol)
    for f in faces: sewer.Add(f)
    sewer.Perform()
    free_edges = sewer.NbFreeEdges()

    solid_maker = BRepBuilderAPI_MakeSolid()
    explorer = TopExp_Explorer(sewer.SewedShape(), TopAbs_SHELL)
    while explorer.More():
        solid_maker.Add(TopoDS.Shell_s(explorer.Current()))
        explorer.Next()

    if not solid_maker.IsDone():
        return None, free_edges

    raw_solid = solid_maker.Solid()

    # ── FIX 1: Orient normals outward ────────────────────────────────────
    # Without this, the sewn solid may have inward normals (inside-out).
    # Cutting the main body with an inside-out solid performs a boolean
    # INTERSECTION instead of subtraction — leaving only the ~145 mm³ boss
    # volume and discarding the 44000+ mm³ main body (exactly what we saw).
    BRepLib.OrientClosedSolid_s(raw_solid)

    return raw_solid, free_edges


def cut_solid_with_tool(main_shape, tool_shape):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    cutter = BRepAlgoAPI_Cut()
    args = TopTools_ListOfShape(); args.Append(main_shape)
    tools = TopTools_ListOfShape(); tools.Append(tool_shape)
    cutter.SetArguments(args); cutter.SetTools(tools)
    cutter.SetFuzzyValue(1e-3); cutter.Build()
    return cutter.Shape() if cutter.IsDone() else main_shape


def extract_largest_solid(shape):
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    solids = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solids.append(Solid(explorer.Current())); explorer.Next()
    if not solids: return None
    def get_vol(s):
        v = s.volume; return v() if callable(v) else v
    return max(solids, key=get_vol)


def watertight_check(solid, log_fn):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    sewer = BRepBuilderAPI_Sewing(0.01)
    explorer = TopExp_Explorer(solid.wrapped, TopAbs_FACE)
    face_count = 0
    while explorer.More():
        sewer.Add(explorer.Current()); face_count += 1; explorer.Next()
    sewer.Perform()
    free_edges = sewer.NbFreeEdges()
    log_fn(f"   Faces in solid : {face_count}")
    log_fn(f"   Free edges     : {free_edges}")
    if free_edges == 0:
        log_fn("   🟢 SUCCESS: Mesh is watertight!")
    else:
        log_fn(f"   🔴 WARNING: {free_edges} free edge(s) — not watertight.")
    return free_edges

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    log_lines = []
    def log(msg=""):
        print(msg); log_lines.append(msg)

    log("=" * 60)
    log("  2_Art4BodyBot — build123d Assembly Script")
    log(f"  Guidelines: G1 → G18  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # Populated inside BuildPart, used outside for OCP G14 cuts
    s6_groups = []
    s7_loops  = []

    # ══════════════════════════════════════════════════════════════════════
    # G1: Annular sketch from S1
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — two 3-point circle profiles...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")
    if not s1_rows:
        log("   ❌ No data in S1. Aborting."); return

    circles = []
    for r in s1_rows:
        if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
            circles.append({"center": center, "radius": radius, "z": r["p1"][2], "label": r["draw_type"]})
            log(f"   ✓ {r['draw_type']}: center=({center[0]:.3f},{center[1]:.3f}), R={radius:.3f}, Z={r['p1'][2]}")

    if len(circles) < 2:
        log(f"   ❌ Expected 2 circles, got {len(circles)}. Aborting."); return

    circles.sort(key=lambda c: c["radius"])
    inner, outer = circles[0], circles[1]
    z_plane_s1 = outer["z"]
    log(f"\n   Inner R={inner['radius']:.3f}  Outer R={outer['radius']:.3f}  Z={z_plane_s1}")

    with BuildPart() as part_builder:

        with BuildSketch(Plane(origin=(0, 0, z_plane_s1), z_dir=(0, 0, 1))):
            with Locations([(outer["center"][0], outer["center"][1])]):
                Circle(outer["radius"])
            with Locations([(inner["center"][0], inner["center"][1])]):
                Circle(inner["radius"], mode=Mode.SUBTRACT)
        log(f"   ✓ Annular sketch: outer R={outer['radius']:.3f}, inner R={inner['radius']:.3f}")
        log("--- [G1] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G2: Extrude annular profile −Z
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G2] Extruding annular profile {EXTRUDE_DEPTH_G2} in −Z...")
        extrude(amount=-EXTRUDE_DEPTH_G2)
        vol = part_builder.part.volume
        log(f"   ✓ Volume = {(vol() if callable(vol) else vol):.4f} mm³")
        log("--- [G2] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G3: Checkpoint
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G3] Checkpoint — annular disc built. Export deferred to end.")
        log("--- [G3] Checkpoint ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G4: Read S2 — Four Hexagons
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G4] Reading S2 — four hexagon profiles...")
        s2_rows = read_csv("Fusion_Coordinates_S2.csv")
        hex_loops = []
        if not s2_rows:
            log("   ❌ No data in S2. Skipping G4-G5.")
        else:
            hex_loops = order_line_segments(s2_rows)
            log(f"   Found {len(hex_loops)} closed polygon(s).")
            for i, loop in enumerate(hex_loops):
                cx = sum(p[0] for p in loop)/len(loop)
                cy = sum(p[1] for p in loop)/len(loop)
                log(f"   Hexagon {i+1}: {len(loop)} pts, centroid=({cx:.3f},{cy:.3f}), Z={loop[0][2]}")
            log("--- [G4] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G5: Cut hexagons −Z
        # ══════════════════════════════════════════════════════════════════
        if hex_loops:
            log(f"\n-> [G5] Cutting {len(hex_loops)} hexagons by {EXTRUDE_DEPTH_G5} in −Z...")
            for i, loop in enumerate(hex_loops):
                with BuildSketch(Plane(origin=(0, 0, loop[0][2]), z_dir=(0, 0, 1))):
                    with BuildLine():
                        pts_2d = [(p[0], p[1]) for p in loop]
                        Polyline(*pts_2d, pts_2d[0])
                    make_face()
                extrude(amount=-EXTRUDE_DEPTH_G5, mode=Mode.SUBTRACT)
                log(f"   ✓ Hexagon {i+1} cut.")
            vol = part_builder.part.volume
            log(f"   Volume after G5 = {(vol() if callable(vol) else vol):.4f} mm³")
            log("--- [G5] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G6: Read S3 — Four circles Z=2.5
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G6] Reading S3 — four 3-point circle profiles...")
        s3_rows = read_csv("Fusion_Coordinates_S3.csv")
        s3_circles = []
        for r in s3_rows:
            if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
                center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                s3_circles.append({"center": center, "radius": radius, "z": r["p1"][2]})
                log(f"   ✓ {r['draw_type']}: center=({center[0]:.3f},{center[1]:.3f}), R={radius:.3f}, Z={r['p1'][2]}")
        log(f"   Total S3 circles: {len(s3_circles)}")
        log("--- [G6] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G7: Cut S3 circles −Z
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G7] Cutting {len(s3_circles)} S3 circles by {EXTRUDE_DEPTH_G7} in −Z...")
        for i, c in enumerate(s3_circles):
            with BuildSketch(Plane(origin=(0, 0, c["z"]), z_dir=(0, 0, 1))):
                with Locations([(c["center"][0], c["center"][1])]):
                    Circle(c["radius"])
            extrude(amount=-EXTRUDE_DEPTH_G7, mode=Mode.SUBTRACT)
            log(f"   ✓ S3 circle {i+1} cut (R={c['radius']:.3f}, Z={c['z']}).")
        vol = part_builder.part.volume
        log(f"   Volume after G7 = {(vol() if callable(vol) else vol):.4f} mm³")
        log("--- [G7] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G8: Read S4 — Four circles Z=4.5
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G8] Reading S4 — four 3-point circle profiles...")
        s4_rows = read_csv("Fusion_Coordinates_S4.csv")
        s4_circles = []
        for r in s4_rows:
            if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
                center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                s4_circles.append({"center": center, "radius": radius, "z": r["p1"][2]})
                log(f"   ✓ {r['draw_type']}: center=({center[0]:.3f},{center[1]:.3f}), R={radius:.3f}, Z={r['p1'][2]}")
        log(f"   Total S4 circles: {len(s4_circles)}")
        log("--- [G8] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G9: Cut S4 circles −Z
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G9] Cutting {len(s4_circles)} S4 circles by {EXTRUDE_DEPTH_G9} in −Z...")
        for i, c in enumerate(s4_circles):
            with BuildSketch(Plane(origin=(0, 0, c["z"]), z_dir=(0, 0, 1))):
                with Locations([(c["center"][0], c["center"][1])]):
                    Circle(c["radius"])
            extrude(amount=-EXTRUDE_DEPTH_G9, mode=Mode.SUBTRACT)
            log(f"   ✓ S4 circle {i+1} cut (R={c['radius']:.3f}, Z={c['z']}).")
        vol = part_builder.part.volume
        log(f"   Volume after G9 = {(vol() if callable(vol) else vol):.4f} mm³")
        log("--- [G9] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G10: Read S5 — Four enclosed line profiles
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G10] Reading S5 — four enclosed line profiles...")
        s5_rows = read_csv("Fusion_Coordinates_S5.csv")
        s5_loops = []
        if not s5_rows:
            log("   ❌ No data in S5. Skipping G10-G11.")
        else:
            s5_loops = order_line_segments(s5_rows)
            log(f"   Found {len(s5_loops)} closed profile(s).")
            for i, loop in enumerate(s5_loops):
                cx = sum(p[0] for p in loop)/len(loop)
                cy = sum(p[1] for p in loop)/len(loop)
                log(f"   Profile {i+1}: {len(loop)} pts, centroid=({cx:.3f},{cy:.3f}), Z={loop[0][2]}")
            log("--- [G10] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G11: Extrude (join) S5 profiles +Z
        # ══════════════════════════════════════════════════════════════════
        if s5_loops:
            log(f"\n-> [G11] Extruding {len(s5_loops)} S5 profiles by {EXTRUDE_DEPTH_G11} in +Z...")
            for i, loop in enumerate(s5_loops):
                with BuildSketch(Plane(origin=(0, 0, loop[0][2]), z_dir=(0, 0, 1))):
                    with BuildLine():
                        pts_2d = [(p[0], p[1]) for p in loop]
                        Polyline(*pts_2d, pts_2d[0])
                    make_face()
                extrude(amount=EXTRUDE_DEPTH_G11)
                log(f"   ✓ Profile {i+1} extruded (join).")
            vol = part_builder.part.volume
            log(f"   Volume after G11 = {(vol() if callable(vol) else vol):.4f} mm³")
            log("--- [G11] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G12: Read S6 — Triangular faces + top quad per boss
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G12] Reading S6 — triangular side faces + top quad lines...")
        s6_rows = read_csv("Fusion_Coordinates_S6.csv")

        if not s6_rows:
            log("   ❌ No data in S6. Skipping G12-G14.")
        else:
            s6_tri_rows  = [r for r in s6_rows if "triangular" in r["draw_type"] and r["p3"]]
            s6_line_rows = [r for r in s6_rows if r["draw_type"] == "line" and r["p2"]]

            boss_tris  = {"A": [], "B": [], "C": [], "D": []}
            boss_lines = {"A": [], "B": [], "C": [], "D": []}

            for r in s6_tri_rows:
                cx = (r["p1"][0]+r["p2"][0]+r["p3"][0])/3
                cy = (r["p1"][1]+r["p2"][1]+r["p3"][1])/3
                boss_tris[boss_quadrant(cx, cy)].append(r)

            for r in s6_line_rows:
                cx = (r["p1"][0]+r["p2"][0])/2
                cy = (r["p1"][1]+r["p2"][1])/2
                boss_lines[boss_quadrant(cx, cy)].append(r)

            for label in ["A", "B", "C", "D"]:
                tri_faces = []
                for r in boss_tris[label]:
                    f = make_triangle_face(r["p1"], r["p2"], r["p3"])
                    if f: tri_faces.append(f)

                top_pts_raw = set()
                for r in boss_lines[label]:
                    top_pts_raw.add(tuple(round(x, 6) for x in r["p1"]))
                    top_pts_raw.add(tuple(round(x, 6) for x in r["p2"]))
                top_quad_pts = sort_pts_by_angle(list(top_pts_raw))

                s6_groups.append({
                    "label":        label,
                    "tri_faces":    tri_faces,
                    "top_quad_pts": top_quad_pts,
                })
                log(f"   Boss {label}: {len(tri_faces)} tri faces, "
                    f"{len(top_quad_pts)} top quad pts (angle-sorted).")

            log(f"   Total S6 groups: {len(s6_groups)}")
            log("--- [G12] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G13: Read S7 — Non-planar pentagonal loops
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G13] Reading S7 — non-planar pentagonal cap loops...")
        s7_rows = read_csv("Fusion_Coordinates_S7.csv")

        if not s7_rows:
            log("   ❌ No data in S7. Skipping G13-G14.")
        else:
            s7_loops = order_line_segments(s7_rows)
            log(f"   Found {len(s7_loops)} closed loop(s).")
            for i, loop in enumerate(s7_loops):
                zs   = sorted(set(round(p[2], 3) for p in loop))
                cx   = sum(p[0] for p in loop)/len(loop)
                cy   = sum(p[1] for p in loop)/len(loop)
                boss = boss_quadrant(cx, cy)
                log(f"   Loop {i+1} → boss {boss}: {len(loop)} pts, Z={zs}, centroid=({cx:.3f},{cy:.3f})")
                if len(zs) > 1:
                    log(f"            ↳ Non-planar — will use fan_triangulate_3d ✓")
            log("--- [G13] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G14: Sew + orient + cut boss solids from main body
    # Runs OUTSIDE BuildPart using OCP directly.
    # ══════════════════════════════════════════════════════════════════════
    current_solid = part_builder.part

    if s6_groups and s7_loops:
        log(f"\n-> [G14] Building 4 boss cut-solids from S6+S7...")

        boss_s7 = {"A": [], "B": [], "C": [], "D": []}
        for loop in s7_loops:
            cx = sum(p[0] for p in loop)/len(loop)
            cy = sum(p[1] for p in loop)/len(loop)
            boss_s7[boss_quadrant(cx, cy)].append(loop)

        for grp in s6_groups:
            label     = grp["label"]
            all_faces = list(grp["tri_faces"])

            # Top quad face (coplanar Z=14.5 — use polygon)
            if len(grp["top_quad_pts"]) >= 3:
                top_face = make_polygon_face(grp["top_quad_pts"])
                if top_face:
                    all_faces.append(top_face)
                else:
                    log(f"   ⚠️  Boss {label}: polygon top face failed, using fan fallback.")
                    all_faces.extend(fan_triangulate_3d(grp["top_quad_pts"]))

            # S7 caps — NON-PLANAR: always use fan_triangulate_3d
            for loop in boss_s7.get(label, []):
                cap_faces = fan_triangulate_3d(loop)
                all_faces.extend(cap_faces)
                log(f"   Boss {label}: S7 cap → {len(cap_faces)} fan triangles "
                    f"(Z spans {sorted(set(round(p[2],3) for p in loop))})")

            log(f"   Boss {label}: sewing {len(all_faces)} faces...")
            boss_solid, free_e = sew_faces_to_solid(all_faces, tol=0.01)
            # ↑ BRepLib.OrientClosedSolid_s() is called inside sew_faces_to_solid()
            #   to ensure outward normals before using as a cut tool.

            if boss_solid:
                log(f"   Boss {label}: sewn ({free_e} free edges), normals oriented. Cutting...")
                result_shape = cut_solid_with_tool(current_solid.wrapped, boss_solid)
                extracted    = extract_largest_solid(result_shape)
                if extracted:
                    current_solid = extracted
                    v = current_solid.volume
                    log(f"   ✓ Boss {label} cut. Volume = {(v() if callable(v) else v):.4f} mm³")
                else:
                    log(f"   ⚠️  Boss {label}: no solid after cut — keeping previous.")
            else:
                log(f"   ❌ Boss {label}: sew failed ({free_e} free edges) — skipping.")

        vol = current_solid.volume
        log(f"   Volume after G14 = {(vol() if callable(vol) else vol):.4f} mm³")
        log("--- [G14] Complete ✓ ---")

    final_solid = current_solid

    # ══════════════════════════════════════════════════════════════════════
    # G15: Read S8 — Four 3-point circles on individual tilted planes
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G15] Reading S8 — four 3-point circles on tilted planes...")

    s8_rows = read_csv("Fusion_Coordinates_S8.csv")
    s8_circles = []

    if not s8_rows:
        log("   ❌ No data in S8. Skipping G15-G16.")
    else:
        for r in s8_rows:
            if "3_point_circle" in r["draw_type"]:
                if r["p1"] and r["p2"] and r["p3"]:
                    center, radius, normal = circle_from_3_points_3d(r["p1"], r["p2"], r["p3"])
                    s8_circles.append({
                        "center": center,
                        "radius": radius,
                        "normal": normal,
                        "label": r["draw_type"],
                    })
                    log(f"   ✓ {r['draw_type']}: center=({center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f}), "
                        f"R={radius:.3f}, normal=({normal[0]:.4f}, {normal[1]:.4f}, {normal[2]:.4f})")

        log(f"   Total S8 circles: {len(s8_circles)}")
        log("--- [G15] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G16: Extrude-cut S8 circles outward-normally by 8 units
    # Uses OCP directly — builds a circular face on each tilted plane,
    # then prism-extrudes along the outward normal and boolean-cuts.
    # ══════════════════════════════════════════════════════════════════════
    if s8_circles:
        log(f"\n-> [G16] Extrude-cutting {len(s8_circles)} S8 circles by {EXTRUDE_DEPTH_G16} outward-normally...")

        import numpy as np
        from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Vec, gp_Circ
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
        from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

        for i, c in enumerate(s8_circles):
            cx, cy, cz = c["center"]
            nx, ny, nz = c["normal"]
            r = c["radius"]

            try:
                # Compute a stable X-reference direction perpendicular to the normal
                n_vec = np.array([nx, ny, nz])
                # Pick a helper vector NOT parallel to the normal
                helper = np.array([0, 0, 1]) if abs(nz) < 0.9 else np.array([1, 0, 0])
                x_ref = np.cross(n_vec, helper)
                x_ref = x_ref / np.linalg.norm(x_ref)

                # Build gp_Ax2 with explicit origin, Z-dir (normal), X-dir
                axis2 = gp_Ax2(
                    gp_Pnt(cx, cy, cz),
                    gp_Dir(nx, ny, nz),
                    gp_Dir(float(x_ref[0]), float(x_ref[1]), float(x_ref[2]))
                )

                # Create a circle on the tilted plane
                circ = gp_Circ(axis2, r)
                edge = BRepBuilderAPI_MakeEdge(circ).Edge()
                wire = BRepBuilderAPI_MakeWire(edge).Wire()
                face = BRepBuilderAPI_MakeFace(wire).Face()

                # Prism-extrude the circular face along the outward normal
                prism_vec = gp_Vec(
                    nx * EXTRUDE_DEPTH_G16,
                    ny * EXTRUDE_DEPTH_G16,
                    nz * EXTRUDE_DEPTH_G16
                )
                prism = BRepPrimAPI_MakePrism(face, prism_vec)

                if prism.IsDone():
                    result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                    extracted = extract_largest_solid(result_shape)
                    if extracted:
                        final_solid = extracted
                        vol = final_solid.volume
                        vol_val = vol() if callable(vol) else vol
                        log(f"   ✓ S8 circle {i+1} ({c['label']}) cut. Volume = {vol_val:.4f} mm³")
                    else:
                        log(f"   ⚠️  S8 circle {i+1}: no solid after cut — keeping previous.")
                else:
                    log(f"   ❌ S8 circle {i+1}: prism extrusion failed.")

            except Exception as e:
                log(f"   ❌ S8 circle {i+1}: error — {e}")

        vol = final_solid.volume
        vol_val = vol() if callable(vol) else vol
        log(f"   Volume after G16 = {vol_val:.4f} mm³")
        log("--- [G16] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G17: Read S9 — Four 3-point circles at Z=0 (flat XY plane)
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G17] Reading S9 — four 3-point circles at Z=0...")

    s9_rows = read_csv("Fusion_Coordinates_S9.csv")
    s9_circles = []

    if not s9_rows:
        log("   ❌ No data in S9. Skipping G17-G18.")
    else:
        for r in s9_rows:
            if "3_point_circle" in r["draw_type"]:
                if r["p1"] and r["p2"] and r["p3"]:
                    center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                    z_val = r["p1"][2]
                    s9_circles.append({
                        "center": center,
                        "radius": radius,
                        "z": z_val,
                        "label": r["draw_type"],
                    })
                    log(f"   ✓ {r['draw_type']}: center=({center[0]:.3f}, {center[1]:.3f}), "
                        f"R={radius:.3f}, Z={z_val}")

        log(f"   Total S9 circles: {len(s9_circles)}")
        log("--- [G17] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G18: Extrude-cut S9 circles by 3 units in +Z
    # Uses OCP: circular face at Z=0 → prism along +Z → boolean cut.
    # ══════════════════════════════════════════════════════════════════════
    if s9_circles:
        log(f"\n-> [G18] Extrude-cutting {len(s9_circles)} S9 circles by {EXTRUDE_DEPTH_G18} in +Z...")

        from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Vec, gp_Circ
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
        from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

        for i, c in enumerate(s9_circles):
            cx, cy = c["center"]
            z_val = c["z"]
            r = c["radius"]

            try:
                # Flat XY plane at Z=z_val, normal pointing +Z
                axis2 = gp_Ax2(gp_Pnt(cx, cy, z_val), gp_Dir(0, 0, 1))
                circ = gp_Circ(axis2, r)
                edge = BRepBuilderAPI_MakeEdge(circ).Edge()
                wire = BRepBuilderAPI_MakeWire(edge).Wire()
                face = BRepBuilderAPI_MakeFace(wire).Face()

                # Prism along +Z
                prism_vec = gp_Vec(0, 0, EXTRUDE_DEPTH_G18)
                prism = BRepPrimAPI_MakePrism(face, prism_vec)

                if prism.IsDone():
                    result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                    extracted = extract_largest_solid(result_shape)
                    if extracted:
                        final_solid = extracted
                        vol = final_solid.volume
                        vol_val = vol() if callable(vol) else vol
                        log(f"   ✓ S9 circle {i+1} ({c['label']}) cut. Volume = {vol_val:.4f} mm³")
                    else:
                        log(f"   ⚠️  S9 circle {i+1}: no solid after cut — keeping previous.")
                else:
                    log(f"   ❌ S9 circle {i+1}: prism extrusion failed.")

            except Exception as e:
                log(f"   ❌ S9 circle {i+1}: error — {e}")

        vol = final_solid.volume
        vol_val = vol() if callable(vol) else vol
        log(f"   Volume after G18 = {vol_val:.4f} mm³")
        log("--- [G18] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # Final: Watertight check + Export STL + Summary
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> Watertight check before export...")
    watertight_check(final_solid, log)

    vol = final_solid.volume
    log(f"\n   Final volume = {(vol() if callable(vol) else vol):.4f} mm³")

    stl_path = os.path.join(BASE_DIR, STL_NAME)
    try:
        export_stl(final_solid, stl_path, tolerance=0.005, angular_tolerance=0.05)
        stl_kb = os.path.getsize(stl_path) / 1024
        log(f"   ✓ Saved: {STL_NAME} ({stl_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STL export failed: {e}")

    log(f"\n{'='*60}")
    log(f"  BUILD COMPLETE — G1 through G18")
    log(f"{'='*60}")

    log_path = os.path.join(BASE_DIR, LOG_NAME)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    print(f"\n📄 Saved summary → {LOG_NAME}")

    print("Displaying in OCP viewer on port 3939...")
    set_port(3939)
    show([final_solid], names=["Art4BodyBot_G1-G18"])


if __name__ == "__main__":
    main()