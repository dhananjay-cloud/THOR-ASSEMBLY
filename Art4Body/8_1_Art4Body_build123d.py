"""
8_1_Art4Body_build123d.py

Build the Art4Body part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4Body.stl

Guidelines executed (in logical order):
  G1 : Read S1 — draw inner and outer circle profiles in global coordinates.
  G2 : Extrude the annular region between circles by 100 units in +Z.
  G4 : Read S2 — draw 4 triangles and 4 trapezium-shaped closed profiles.
  G5 : Extrude-cut the G4 profiles by 55 units in −Z.
  G6 : Read S3 — draw closed profiles (inner geometries).
  G7 : Extrude-join the G6 profiles by 55 units in +Z to merge with the body.
  G8 : Read S4 — draw 4 hexagon profiles.
  G9 : Extrude-cut the G8 hexagons symmetrically up to 51 units in both directions.
  G10: Read S5 — draw 5 circle profiles (automatically determines XY, XZ, or YZ planes).
  G11: Extrude-cut the 5 circles symmetrically up to 55 units in both directions.
  G12: Read S7 — draw inner and outer circle profiles.
  G13: Extrude-cut S7 inner circle radially inward by 5, outer circle radially outward by 5.
  G14: Read S8 — draw inner and outer circle profiles.
  G15: Extrude-cut S8 inner circle radially inward by 5, outer circle radially outward by 5.
  G16: Read S9 — draw inner and outer circle profiles.
  G17: Extrude-cut S9 inner circle radially inward by 5, outer circle radially outward by 5.
  G18: Read S10— draw inner and outer circle profiles.
  G19: Extrude-cut S10 inner circle radially inward by 5, outer circle radially outward by 5.
  G20: Read S11— draw mathematically exact dome arcs & lines + reference axis.
  G21: Revolve the G20 profile 180° around the Y-axis to form the top dome.
  G22: Read S12— draw enclosed profile from arc and 3 lines (ignoring construction line).
  G23: Extrude-cut S12 profile by 60 units symmetrically in each direction.
  G24: Read S13— draw closed 6-line polygon profile.
  G25: Extrude-cut S13 profile by 20 units in +Z direction.
  G26: Read S14— draw 4 circles (2 concentric pairs).
  G27: Extrude-cut S14 inner circles symmetrically 5 units, outer outwards by 5.
  G28: Read S15— draw 2 circles (1 concentric pair).
  G29: Extrude-cut S15 inner circle symmetrically 5 units, outer outwards by 5.
  G30: Read S16— draw 1 circle.
  G31: Extrude-cut S16 circle by 5 units strictly radially inward.
  G32: Read S17— draw 1 circle profile on YZ plane.
  G33: Extrude-join G32 profile by 6.5 units in -X with expanding 45.43° taper.
  G34: Read S18— draw 2 hexagon profiles.
  G35: Extrude-cut G34 profiles by 4 units in -X direction.
  G36: Read S19— draw 1 circle profile and 1 closed profile (lines+arcs).
  G37: Extrude-cut circle 10 units outward (-X); non-circle 10 units inward (+X).
  G38: Read S20— draw rectangular profile (from lines) and 2 circles.
  G39: Extrude-cut solid rectangle outward by 10, cut circles inward by 10.
  G40: Read S21— draw 1 enclosed profile made of lines and an arc.
  G41: Extrude-cut G40 profile by 15 units along the negative Z direction.
  G42: Mirror all tool bodies from G32-G41 across the global YZ plane.
  G3 : (deferred / final) Clean geometry, watertight check + export STL/STEP + write summary.

Execution order: G1 → G2 → G4 → G5 → G6 → G7 → G8 → G9 → G10 → G11 
                 → G12 → G13 → G14 → G15 → G16 → G17 → G18 → G19 
                 → G20 → G21 → G22 → G23 → G24 → G25 → G26 → G27 
                 → G28 → G29 → G30 → G31 → G32 → G33 → G34 → G35 
                 → G36 → G37 → G38 → G39 → G40 → G41 → G42 → G3
"""

import os
import csv
import math
from datetime import datetime

from build123d import *
from ocp_vscode import show, set_port

# ── PATHS & NAMING ────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/8_Art4Body"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_START  = 1
G_END    = 42   # full script: G1–G42; G3 is the export step deferred to end
STL_NAME = f"8_Art4Body_G_{G_START}_{G_END}.stl"
LOG_NAME = f"8_Art4Body_summary_G_{G_START}_{G_END}.txt"


# ════════════════════════════════════════════════════════════════════════════
# CSV READER
# ════════════════════════════════════════════════════════════════════════════

def read_csv(filename):
    """
    Read a Fusion_Coordinates_Sx.csv from csv_merged.
    Returns a list of dicts: {draw_type, p1, p2 (or None), p3 (or None)}.
    """
    filepath = os.path.join(CSV_DIR, filename)
    if not os.path.exists(filepath):
        print(f"⚠️  Warning: {filename} not found at {filepath}")
        return []
    rows = []
    with open(filepath, "r") as f:
        for row in csv.DictReader(f):
            def _f(v):
                v = v.strip()
                return None if v in ("", "NA") else float(v)

            x1, y1, z1 = _f(row["X1"]), _f(row["Y1"]), _f(row["Z1"])
            x2, y2, z2 = _f(row["X2"]), _f(row["Y2"]), _f(row["Z2"])
            x3, y3, z3 = _f(row["X3"]), _f(row["Y3"]), _f(row["Z3"])

            parsed = {
                "draw_type": row["Draw Type"].strip().lower(),
                "p1": (x1, y1, z1) if x1 is not None else None,
                "p2": (x2, y2, z2) if x2 is not None else None,
                "p3": (x3, y3, z3) if x3 is not None else None,
            }
            rows.append(parsed)
    return rows


# ════════════════════════════════════════════════════════════════════════════
# GEOMETRY HELPERS
# ════════════════════════════════════════════════════════════════════════════

def get_circle_plane_and_radius(p1, p2, p3):
    A, B, C = p1, p2, p3
    
    a = (A[0]-C[0], A[1]-C[1], A[2]-C[2])
    b = (B[0]-C[0], B[1]-C[1], B[2]-C[2])
    
    cross_ab = (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    )
    
    len_cross_sq = cross_ab[0]**2 + cross_ab[1]**2 + cross_ab[2]**2
    if len_cross_sq < 1e-12:
        raise ValueError("Points are collinear")
        
    dot_aa = a[0]**2 + a[1]**2 + a[2]**2
    dot_bb = b[0]**2 + b[1]**2 + b[2]**2
    
    term1 = (dot_aa*b[0] - dot_bb*a[0], dot_aa*b[1] - dot_bb*a[1], dot_aa*b[2] - dot_bb*a[2])
    num = (
        term1[1]*cross_ab[2] - term1[2]*cross_ab[1],
        term1[2]*cross_ab[0] - term1[0]*cross_ab[2],
        term1[0]*cross_ab[1] - term1[1]*cross_ab[0]
    )
    
    den = 2 * len_cross_sq
    center = (
        C[0] + num[0]/den,
        C[1] + num[1]/den,
        C[2] + num[2]/den
    )
    
    r = math.sqrt((center[0]-A[0])**2 + (center[1]-A[1])**2 + (center[2]-A[2])**2)
    len_cross = math.sqrt(len_cross_sq)
    n = (cross_ab[0]/len_cross, cross_ab[1]/len_cross, cross_ab[2]/len_cross)
    
    dot_n_c = n[0]*center[0] + n[1]*center[1] + n[2]*center[2]
    if dot_n_c < 0:
        n = (-n[0], -n[1], -n[2])
        
    return Plane(origin=center, z_dir=n), r


def group_polygons_3d(rows, tol=1e-3):
    def close_pts(a, b):
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) < tol

    segments = []
    for r in rows:
        if r["draw_type"] == "line" and r["p1"] and r["p2"]:
            a = (round(r["p1"][0], 4), round(r["p1"][1], 4), round(r["p1"][2], 4))
            b = (round(r["p2"][0], 4), round(r["p2"][1], 4), round(r["p2"][2], 4))
            if not close_pts(a, b):
                segments.append((a, b))

    used = [False] * len(segments)
    polys = []

    for start_idx, (sa, sb) in enumerate(segments):
        if used[start_idx]: continue
        chain = [sa, sb]
        used_tmp = [False] * len(segments)
        used_tmp[start_idx] = True

        while True:
            current_end = chain[-1]
            found = False
            for j, (ja, jb) in enumerate(segments):
                if used_tmp[j] or used[j]: continue
                if close_pts(current_end, ja):
                    chain.append(jb)
                    used_tmp[j] = True
                    found = True
                    break
                elif close_pts(current_end, jb):
                    chain.append(ja)
                    used_tmp[j] = True
                    found = True
                    break
            if not found:
                break 
            if close_pts(chain[-1], chain[0]) and len(chain) > 3:
                for j, flag in enumerate(used_tmp):
                    if flag: used[j] = True
                polys.append(chain[:-1])
                break

    return polys


def create_faces_from_polys(polys_3d):
    faces = []
    for poly in polys_3d:
        edges = [Line(poly[i], poly[(i+1)%len(poly)]) for i in range(len(poly))]
        wire = Wire.combine(edges)[0]
        faces.append(Face(wire))
    return faces


def keep_main_body(cad_obj):
    if type(cad_obj).__name__ == 'ShapeList' or isinstance(cad_obj, list):
        return max(cad_obj, key=lambda s: s.volume)
    return cad_obj


def get_volume(solid):
    if hasattr(solid, "volume"):
        v = solid.volume
        return v() if callable(v) else v
    elif hasattr(solid, "__iter__"):
        return sum(s.volume for s in solid)
    return 0.0


def watertight_check(solid, log_fn):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer

    sewer = BRepBuilderAPI_Sewing(0.01)
    explorer = TopExp_Explorer(solid.wrapped, TopAbs_FACE)
    face_count = 0
    while explorer.More():
        sewer.Add(explorer.Current())
        face_count += 1
        explorer.Next()
    sewer.Perform()
    free_edges = sewer.NbFreeEdges()

    log_fn(f"   Faces in solid : {face_count}")
    log_fn(f"   Free edges     : {free_edges}")
    if free_edges == 0:
        log_fn("   🟢 SUCCESS: Mesh is watertight!")
    else:
        log_fn(f"   🔴 WARNING: {free_edges} free edge(s) — mesh is NOT watertight.")
    return free_edges


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    log_lines = []

    def log(msg=""):
        print(msg)
        log_lines.append(msg)

    log("=" * 65)
    log("  8_Art4Body — build123d Assembly Script")
    log(f"  Guidelines: G1 → G42  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 65)

    # ══════════════════════════════════════════════════════════════════════
    # G1: Read S1 — draw inner and outer circle profiles.
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — inner and outer circle profiles ...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")

    circle_params = []
    for row in s1_rows:
        if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
            plane, r = get_circle_plane_and_radius(row["p1"], row["p2"], row["p3"])
            circle_params.append({"plane": plane, "r": r})

    circle_params.sort(key=lambda c: c["r"])
    c_inner = circle_params[0]
    c_outer = circle_params[1]

    log(f"   → Inner R={c_inner['r']:.4f}  Outer R={c_outer['r']:.4f}")
    log("--- [G1] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G2: Extrude annular region 100 units in +Z
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G2] Extruding annular ring by 100 units in +Z ...")

    with BuildPart() as part:
        with BuildSketch(c_outer["plane"]):
            Circle(c_outer["r"])
            Circle(c_inner["r"], mode=Mode.SUBTRACT)
        extrude(amount=100.0, dir=(0, 0, 1))

    final_solid = keep_main_body(part.part)
    vol = get_volume(final_solid)
    log(f"   ✓ Base tube body created. Volume = {vol:.4f} mm³")
    log("--- [G2] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G4 & G5: Read S2 — 4 triangles & 4 trapeziums, Extrude-cut 55 in −Z
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G4] Reading S2 — triangles and trapeziums ...")
    s2_rows = read_csv("Fusion_Coordinates_S2.csv")
    polys_s2 = group_polygons_3d(s2_rows)
    faces_s2 = create_faces_from_polys(polys_s2)
    
    log(f"\n-> [G5] Extrude-cutting {len(faces_s2)} G4 profiles by 55 units in −Z ...")
    if faces_s2:
        with BuildPart() as cut_g5:
            extrude(faces_s2, amount=55.0, dir=(0, 0, -1))
        final_solid = keep_main_body(final_solid - cut_g5.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Step cuts completed. Volume = {vol:.4f} mm³")
    log("--- [G4 & G5] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G6 & G7: Read S3 — closed profiles, Extrude-join 55 in +Z
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G6] Reading S3 — inner closed profiles ...")
    s3_rows = read_csv("Fusion_Coordinates_S3.csv")
    polys_s3 = group_polygons_3d(s3_rows)
    faces_s3 = create_faces_from_polys(polys_s3)
    
    log(f"\n-> [G7] Extrude-joining {len(faces_s3)} G6 profiles by 55 units in +Z ...")
    if faces_s3:
        with BuildPart() as join_g7:
            extrude(faces_s3, amount=55.0, dir=(0, 0, 1))
        final_solid = keep_main_body(final_solid + join_g7.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Join operation completed. Volume = {vol:.4f} mm³")
    log("--- [G6 & G7] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G8 & G9: Read S4 — 4 hexagons, Extrude-cut symmetrically up to 51
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G8] Reading S4 — 4 hexagon profiles ...")
    s4_rows = read_csv("Fusion_Coordinates_S4.csv")
    polys_s4 = group_polygons_3d(s4_rows)
    faces_s4 = create_faces_from_polys(polys_s4)
    
    log(f"\n-> [G9] Symmetrical extrude-cut ({len(faces_s4)} profiles, 51 units both ways) ...")
    if faces_s4:
        with BuildPart() as cut_g9:
            extrude(faces_s4, amount=51.0, both=True)
        final_solid = keep_main_body(final_solid - cut_g9.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Hexagon pockets cut. Volume = {vol:.4f} mm³")
    log("--- [G8 & G9] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G10 & G11: Read S5 — 5 circles, Extrude-cut symmetrically up to 55
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G10] Reading S5 — 5 circle profiles ...")
    s5_rows = read_csv("Fusion_Coordinates_S5.csv")
    
    log("\n-> [G11] Symmetrical extrude-cut (55 units both ways) ...")
    if s5_rows:
        with BuildPart() as cut_g11:
            for row in s5_rows:
                if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
                    plane, r = get_circle_plane_and_radius(row["p1"], row["p2"], row["p3"])
                    with BuildSketch(plane):
                        Circle(r)
            extrude(amount=55.0, both=True)
        final_solid = keep_main_body(final_solid - cut_g11.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Circular hole patterns cut. Volume = {vol:.4f} mm³")
    log("--- [G10 & G11] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G12 to G19: Legacy 2-circle processing (S7, S8, S9, S10)
    # ══════════════════════════════════════════════════════════════════════
    def process_side_hole_csv(filename, g_read, g_cut):
        nonlocal final_solid
        log(f"\n-> [{g_read}] Reading {filename} — inner and outer circle profiles ...")
        rows = read_csv(filename)
        
        c_params = []
        for row in rows:
            if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
                plane, r = get_circle_plane_and_radius(row["p1"], row["p2"], row["p3"])
                c_params.append({"plane": plane, "r": r})
                
        if len(c_params) < 2: return

        c_params.sort(key=lambda c: c["r"])
        hole_inner = c_params[0]
        hole_outer = c_params[1]
        
        log(f"   → Inner R={hole_inner['r']:.4f} | Outer R={hole_outer['r']:.4f}")
        log(f"--- [{g_read}] Complete ✓ ---")

        log(f"\n-> [{g_cut}] Extrude-cutting {filename} profiles (Inner inward 5, Outer outward 5) ...")
        with BuildPart() as cut_hole:
            with BuildSketch(hole_outer["plane"]):
                Circle(hole_outer["r"])
            extrude(amount=5.0) 
            
            with BuildSketch(hole_inner["plane"]):
                Circle(hole_inner["r"])
            extrude(amount=5.0, both=True)
            
        final_solid = keep_main_body(final_solid - cut_hole.part)
        log(f"   ✓ Hole cuts completed. Volume = {get_volume(final_solid):.4f} mm³")
        log(f"--- [{g_cut}] Complete ✓ ---")

    process_side_hole_csv("Fusion_Coordinates_S7.csv", "G12", "G13")
    process_side_hole_csv("Fusion_Coordinates_S8.csv", "G14", "G15")
    process_side_hole_csv("Fusion_Coordinates_S9.csv", "G16", "G17")
    process_side_hole_csv("Fusion_Coordinates_S10.csv", "G18", "G19")

    # ══════════════════════════════════════════════════════════════════════
    # G20 & G21: Read S11 — 2 lines, 2 exact arcs + ref line → Revolve dome
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G20] Reading S11 — mathematically exact arcs for dome profile ...")
    s11_rows = read_csv("Fusion_Coordinates_S11.csv")
    
    dome_edges = []
    ref_line = None
    
    for r in s11_rows:
        if r["draw_type"] == "line" and r["p1"] and r["p2"]:
            if abs(r["p1"][0]) < 1e-3 and abs(r["p2"][0]) < 1e-3 and \
               abs(r["p1"][2] - 100.0) < 1e-3 and abs(r["p2"][2] - 100.0) < 1e-3:
                if (abs(r["p1"][1]) < 1e-3) or (abs(r["p2"][1]) < 1e-3):
                    ref_line = r
                    continue
            dome_edges.append(Line(r["p1"], r["p2"]))
            
        elif "3_point_arc" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            dome_edges.append(ThreePointArc(r["p1"], r["p2"], r["p3"]))

    log(f"   → Captured {len(dome_edges)} profile segments (exact radii 50 & 55).")
    log("--- [G20] Complete ✓ ---")
    
    log("\n-> [G21] Revolving S11 profile 180° around reference axis ...")
    if dome_edges and ref_line:
        with BuildPart() as dome_part:
            p1_ref = ref_line["p1"]
            rev_axis = Axis(p1_ref, (0, 1, 0))
            dome_faces = [Face(w) for w in Wire.combine(dome_edges)]
            revolve(dome_faces[0], axis=rev_axis, revolution_arc=180)
            
        final_solid = keep_main_body(final_solid + dome_part.part)
        vol = get_volume(final_solid)
        log(f"   ✓ 180° mathematically exact dome revolve completed. Volume = {vol:.4f} mm³")
    log("--- [G21] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G22 & G23: Read S12 — arc + 3 lines → Extrude-cut symmetrically
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G22] Reading S12 — closed profile (arc + lines) ...")
    s12_rows = read_csv("Fusion_Coordinates_S12.csv")
    s12_edges = []
    
    for r in s12_rows:
        if r["draw_type"] == "line" and r["p1"] and r["p2"]:
            if (abs(r["p1"][0]) < 1e-3 and abs(r["p1"][1]) < 1e-3 and abs(r["p1"][2]) < 1e-3) or \
               (abs(r["p2"][0]) < 1e-3 and abs(r["p2"][1]) < 1e-3 and abs(r["p2"][2]) < 1e-3):
                continue
            s12_edges.append(Line(r["p1"], r["p2"]))
        elif "3_point_arc" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            s12_edges.append(ThreePointArc(r["p1"], r["p2"], r["p3"]))

    log(f"   → Captured {len(s12_edges)} profile segments for cut.")
    log("--- [G22] Complete ✓ ---")

    log("\n-> [G23] Extrude-cutting G22 profile by 60 units symmetrically ...")
    if s12_edges:
        with BuildPart() as cut_g23:
            s12_faces = [Face(w) for w in Wire.combine(s12_edges)]
            extrude(s12_faces, amount=60.0, both=True)
            
        final_solid = keep_main_body(final_solid - cut_g23.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Symmetrical profile cut completed. Volume = {vol:.4f} mm³")
    log("--- [G23] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G24 & G25: Read S13 — 6-line closed polygon → Extrude-cut +Z
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G24] Reading S13 — 6-line closed profile ...")
    s13_rows = read_csv("Fusion_Coordinates_S13.csv")
    
    polys_s13 = group_polygons_3d(s13_rows)
    faces_s13 = create_faces_from_polys(polys_s13)
    
    log(f"   → Captured {len(faces_s13)} face(s).")
    log("--- [G24] Complete ✓ ---")

    log("\n-> [G25] Extrude-cutting G24 profile by 20 units in +Z ...")
    if faces_s13:
        with BuildPart() as cut_g25:
            extrude(faces_s13, amount=20.0, dir=(0, 0, 1))
            
        final_solid = keep_main_body(final_solid - cut_g25.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Extrude cut (+Z) completed. Volume = {vol:.4f} mm³")
    log("--- [G25] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # Advanced Multi-Hole Processing (G26 through G31)
    # ══════════════════════════════════════════════════════════════════════
    def process_multiple_holes(filename, g_read, g_cut):
        nonlocal final_solid
        log(f"\n-> [{g_read}] Reading {filename} — circle profiles ...")
        rows = read_csv(filename)
        
        c_params = []
        for row in rows:
            if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
                plane, r = get_circle_plane_and_radius(row["p1"], row["p2"], row["p3"])
                c_params.append({"plane": plane, "r": r})
                
        if not c_params:
            return

        groups = []
        for c in c_params:
            placed = False
            for g in groups:
                c1_orig = c["plane"].origin
                c2_orig = g[0]["plane"].origin
                dist = math.sqrt(sum((a-b)**2 for a,b in zip(c1_orig, c2_orig)))
                if dist < 1.0:
                    g.append(c)
                    placed = True
                    break
            if not placed:
                groups.append([c])

        log(f"   → Found {len(c_params)} total circles, formed {len(groups)} hole group(s).")
        log(f"--- [{g_read}] Complete ✓ ---")

        log(f"\n-> [{g_cut}] Extrude-cutting {filename} grouped profiles ...")
        with BuildPart() as cut_hole:
            for idx, g in enumerate(groups):
                g.sort(key=lambda c: c["r"])
                
                if len(g) >= 2:
                    hole_inner = g[0]
                    hole_outer = g[1]
                    log(f"      Group {idx+1}: Concentric pair (Inner R={hole_inner['r']:.2f}, Outer R={hole_outer['r']:.2f})")
                    
                    with BuildSketch(hole_outer["plane"]):
                        Circle(hole_outer["r"])
                    extrude(amount=5.0) 
                    
                    with BuildSketch(hole_inner["plane"]):
                        Circle(hole_inner["r"])
                    extrude(amount=5.0, both=True)
                
                elif len(g) == 1:
                    hole = g[0]
                    log(f"      Group {idx+1}: Single inward cut (R={hole['r']:.2f})")
                    with BuildSketch(hole["plane"]):
                        Circle(hole["r"])
                    extrude(amount=-5.0)
                    
        final_solid = keep_main_body(final_solid - cut_hole.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Advanced hole cuts completed. Volume = {vol:.4f} mm³")
        log(f"--- [{g_cut}] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G26 & G27: Read S14 — 4 circles (2 concentric pairs)
    # ══════════════════════════════════════════════════════════════════════
    process_multiple_holes("Fusion_Coordinates_S14.csv", "G26", "G27")

    # ══════════════════════════════════════════════════════════════════════
    # G28 & G29: Read S15 — 2 circles (1 concentric pair)
    # ══════════════════════════════════════════════════════════════════════
    process_multiple_holes("Fusion_Coordinates_S15.csv", "G28", "G29")

    # ══════════════════════════════════════════════════════════════════════
    # G30 & G31: Read S16 — 1 circle (single strictly inward cut)
    # ══════════════════════════════════════════════════════════════════════
    process_multiple_holes("Fusion_Coordinates_S16.csv", "G30", "G31")

    # ======================================================================
    # PREPARATION FOR G42: Track tool bodies from G32 to G41
    # ======================================================================
    mirror_adds = []
    mirror_cuts = []

    # ══════════════════════════════════════════════════════════════════════
    # G32 & G33: Read S17 — 1 circle → Extrude-join with taper in -X
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G32] Reading S17 — circle profile ...")
    s17_rows = read_csv("Fusion_Coordinates_S17.csv")
    s17_circles = []
    for row in s17_rows:
        if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
            plane, r = get_circle_plane_and_radius(row["p1"], row["p2"], row["p3"])
            s17_circles.append({"plane": plane, "r": r})
    
    log(f"   → Captured {len(s17_circles)} circle(s) from S17.")
    log("--- [G32] Complete ✓ ---")

    log("\n-> [G33] Extruding S17 profile by 6.5 units in -X with expanding 45.43° taper to Join ...")
    if s17_circles:
        with BuildPart() as ext_g33:
            c = s17_circles[0]
            with BuildSketch(c["plane"]):
                Circle(c["r"])
            extrude(amount=6.5, taper=-45.43)
            
        mirror_adds.append(ext_g33.part) 
        final_solid = keep_main_body(final_solid + ext_g33.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Tapered extrusion (Join) completed. Volume = {vol:.4f} mm³")
    log("--- [G33] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G34 & G35: Read S18 — 2 hexagons → Extrude-cut in -X
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G34] Reading S18 — 2 hexagon profiles ...")
    s18_rows = read_csv("Fusion_Coordinates_S18.csv")
    
    polys_s18 = group_polygons_3d(s18_rows)
    faces_s18 = create_faces_from_polys(polys_s18)
    
    log(f"   → Captured {len(faces_s18)} hexagon face(s).")
    log("--- [G34] Complete ✓ ---")

    log("\n-> [G35] Extrude-cutting G34 profiles by 4 units in -X direction ...")
    if faces_s18:
        with BuildPart() as cut_g35:
            extrude(faces_s18, amount=4.0, dir=(-1, 0, 0))
            
        mirror_cuts.append(cut_g35.part) 
        final_solid = keep_main_body(final_solid - cut_g35.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Hexagon extrude-cut completed. Volume = {vol:.4f} mm³")
    log("--- [G35] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G36 & G37: Read S19 — 1 circle, 1 non-circle profile → Extrude-cuts
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G36] Reading S19 — circle and line/arc profiles ...")
    s19_rows = read_csv("Fusion_Coordinates_S19.csv")
    
    s19_edges = []
    s19_circles = []
    
    for r in s19_rows:
        if "circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            plane, rad = get_circle_plane_and_radius(r["p1"], r["p2"], r["p3"])
            s19_circles.append({"plane": plane, "r": rad})
        elif "line" in r["draw_type"] and r["p1"] and r["p2"]:
            s19_edges.append(Line(r["p1"], r["p2"]))
        elif "arc" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            s19_edges.append(ThreePointArc(r["p1"], r["p2"], r["p3"]))

    log(f"   → Captured {len(s19_circles)} circle(s) and {len(s19_edges)} line/arc segments.")
    log("--- [G36] Complete ✓ ---")

    log("\n-> [G37] Extrude-cutting S19 profiles ...")
    
    if s19_circles:
        with BuildPart() as cut_g37_circle:
            c = s19_circles[0]
            with BuildSketch(c["plane"]):
                Circle(c["r"])
            extrude(amount=10.0, dir=(-1, 0, 0))
        mirror_cuts.append(cut_g37_circle.part)
        final_solid = keep_main_body(final_solid - cut_g37_circle.part)

    if s19_edges:
        with BuildPart() as cut_g37_poly:
            s19_faces = [Face(w) for w in Wire.combine(s19_edges)]
            extrude(s19_faces, amount=10.0, dir=(1, 0, 0))
        mirror_cuts.append(cut_g37_poly.part)
        final_solid = keep_main_body(final_solid - cut_g37_poly.part)

    vol = get_volume(final_solid)
    log(f"   → Volume after G37 = {vol:.4f} mm³")
    log("--- [G37] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G38 & G39: Read S20 — rectangle + 2 circles → Extrude-cuts
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G38] Reading S20 — rectangular profile and circles ...")
    s20_rows = read_csv("Fusion_Coordinates_S20.csv")
    
    s20_circles = []
    s20_lines = []
    
    for r in s20_rows:
        if "circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            plane, rad = get_circle_plane_and_radius(r["p1"], r["p2"], r["p3"])
            s20_circles.append({"plane": plane, "r": rad})
        elif "line" in r["draw_type"] and r["p1"] and r["p2"]:
            s20_lines.append(r)
            
    polys_s20 = group_polygons_3d(s20_lines)
    faces_s20 = create_faces_from_polys(polys_s20)
    
    log(f"   → Captured {len(s20_circles)} circle(s) and {len(faces_s20)} rectangular face(s).")
    log("--- [G38] Complete ✓ ---")

    log("\n-> [G39] Extrude-cutting S20 profiles ...")
    if faces_s20:
        with BuildPart() as cut_g39_rect:
            extrude(faces_s20, amount=10.0, dir=(-1, 0, 0))
        mirror_cuts.append(cut_g39_rect.part)
        final_solid = keep_main_body(final_solid - cut_g39_rect.part)

    if s20_circles:
        with BuildPart() as cut_g39_circ:
            for c in s20_circles:
                with BuildSketch(c["plane"]):
                    Circle(c["r"])
            extrude(amount=10.0, dir=(1, 0, 0))
        mirror_cuts.append(cut_g39_circ.part)
        final_solid = keep_main_body(final_solid - cut_g39_circ.part)

    vol = get_volume(final_solid)
    log(f"   → Volume after G39 = {vol:.4f} mm³")
    log("--- [G39] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G40 & G41: Read S21 — lines + arc → Extrude-cut in -Z
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G40] Reading S21 — enclosed profile (lines + arc) ...")
    s21_rows = read_csv("Fusion_Coordinates_S21.csv")
    
    s21_edges = []
    for r in s21_rows:
        if "line" in r["draw_type"] and r["p1"] and r["p2"]:
            s21_edges.append(Line(r["p1"], r["p2"]))
        elif "3_point_arc" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            s21_edges.append(ThreePointArc(r["p1"], r["p2"], r["p3"]))
            
    log(f"   → Captured {len(s21_edges)} segments for S21 profile.")
    log("--- [G40] Complete ✓ ---")

    log("\n-> [G41] Extrude-cutting G40 profile by 15 units in -Z direction ...")
    if s21_edges:
        with BuildPart() as cut_g41:
            s21_wire = Wire.combine(s21_edges)[0]
            z_level = s21_rows[0]["p1"][2]
            with BuildSketch(Plane(origin=(0, 0, z_level), z_dir=(0, 0, 1))):
                add(s21_wire)
                make_face()
            extrude(amount=-15.0)
            
        mirror_cuts.append(cut_g41.part)
        final_solid = keep_main_body(final_solid - cut_g41.part)
        vol = get_volume(final_solid)
        log(f"   ✓ S21 extrude-cut completed. Volume = {vol:.4f} mm³")
    log("--- [G41] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G42: Mirror G32-G41 Operations across Global YZ Plane
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G42] Mirroring G32-G41 operations across global YZ plane ...")
    
    if mirror_adds:
        for tool in mirror_adds:
            m_tool = mirror(tool, about=Plane.YZ)
            final_solid = keep_main_body(final_solid + m_tool)
        log(f"   ✓ Mirrored {len(mirror_adds)} addition(s).")
        
    if mirror_cuts:
        for tool in mirror_cuts:
            m_tool = mirror(tool, about=Plane.YZ)
            final_solid = keep_main_body(final_solid - m_tool)
        log(f"   ✓ Mirrored {len(mirror_cuts)} cut(s).")

    vol = get_volume(final_solid)
    log(f"   → Volume after G42 = {vol:.4f} mm³")
    log("--- [G42] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G3 (FINAL): Clean geometry, Watertight check + export STL/STEP + write summary
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n{'='*65}")
    log("  [G3]  PRE-EXPORT CHECKS & STL/STEP EXPORT")
    log(f"{'='*65}")

    # 1. CLEAN THE GEOMETRY
    # This heals the mesh and removes microscopic residual edges from the boolean operations
    final_solid = final_solid.clean()

    log("\n-> [G3] Watertight check ...")
    free_edges = watertight_check(final_solid, log)

    final_vol = get_volume(final_solid)
    log(f"\n   Final volume = {final_vol:.4f} mm³")

    # 2. EXPORT HIGH-RES STL (For your comparison script)
    stl_path = os.path.join(BASE_DIR, STL_NAME)
    try:
        # High precision to prevent criss-crossing/flipped normals
        export_stl(final_solid, stl_path, tolerance=0.001, angular_tolerance=0.05)
        stl_kb = os.path.getsize(stl_path) / 1024
        log(f"   ✓ STL saved  : {STL_NAME}  ({stl_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STL export failed: {e}")

    # 3. EXPORT STEP FILE (For flawless Fusion 360 import)
    step_name = STL_NAME.replace(".stl", ".step")
    step_path = os.path.join(BASE_DIR, step_name)
    try:
        export_step(final_solid, step_path)
        step_kb = os.path.getsize(step_path) / 1024
        log(f"   ✓ STEP saved : {step_name}  ({step_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STEP export failed: {e}")

    log(f"\n{'='*65}")
    log("  BUILD COMPLETE — G1 through G42")
    log(f"{'='*65}")

    # ── Write summary log ────────────────────────────────────────────────
    log_path = os.path.join(BASE_DIR, LOG_NAME)
    try:
        with open(log_path, "w") as f:
            f.write("\n".join(log_lines))
        print(f"\n📄 Summary saved → {LOG_NAME}")
    except Exception as e:
        print(f"❌ Could not save summary: {e}")

    # ── OCP viewer ───────────────────────────────────────────────────────
    print("\nDisplaying in OCP viewer on port 3939 ...")
    set_port(3939)
    show([final_solid], names=["Art4Body_G1-G42"])


if __name__ == "__main__":
    main()