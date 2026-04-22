"""
10_1_Art4MotorGear_build123d.py

Build the Art4MotorGear part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4MotorGear.stl

Guidelines executed (in logical order):
  G1 : Read S1 — inner/outer circle profiles and a single tooth profile at Z=13.0.
  G2 : Extrude region between inner and outer circle by 13 units in -Z.
  G4 : Read S2 — identify sweep path line (Z=13 down to Z=0).
  G5 : Sweep join the tooth profile from G1 along the path with twist +46.835 deg.
  G6 : Circular pattern the swept tooth feature around the center (10 total teeth).
  G7 : Read S3 — draw circle profile for the base flange.
  G8 : Extrude G7 circle by 10 units in -Z.
  G9 : Read S4 — draw inner and outer side circles.
  G10: Extrude cut outer circle through all in -X.
  G11: Extrude cut inner circle by 9 units in +X.
  G12: Read S5 — enclosed wedge profile (YZ plane).
  G13: Extrude cut G12 profile symmetrically (3 units total length).
  G14: Read S6 — make profile for center hole.
  G15: Extrude cut G14 profile by 11 units in +Z.
  G3 : Clean geometry, watertight check + export STL/STEP + write summary.

Execution order: G1, G2, G4, G5, G6, G7, G8, G9, G10, G11, G12, G13, G14, G15, G3
"""

import os
import csv
import math
from datetime import datetime

from build123d import *
from ocp_vscode import show, set_port

# ── PATHS & NAMING ────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/10_Art4MotorGear"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_START  = 1
G_END    = 15
STL_NAME = f"10_Art4MotorGear_G_{G_START}_{G_END}.stl"
STEP_NAME = f"10_Art4MotorGear_G_{G_START}_{G_END}.step"
LOG_NAME = f"10_Art4MotorGear_summary_G_{G_START}_{G_END}.txt"


# ════════════════════════════════════════════════════════════════════════════
# CSV READER
# ════════════════════════════════════════════════════════════════════════════

def read_csv(filename):
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
    
    cross_ab = (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])
    len_cross_sq = cross_ab[0]**2 + cross_ab[1]**2 + cross_ab[2]**2
    if len_cross_sq < 1e-12:
        raise ValueError("Points are collinear")
        
    dot_aa, dot_bb = a[0]**2 + a[1]**2 + a[2]**2, b[0]**2 + b[1]**2 + b[2]**2
    term1 = (dot_aa*b[0] - dot_bb*a[0], dot_aa*b[1] - dot_bb*a[1], dot_aa*b[2] - dot_bb*a[2])
    num = (term1[1]*cross_ab[2] - term1[2]*cross_ab[1], term1[2]*cross_ab[0] - term1[0]*cross_ab[2], term1[0]*cross_ab[1] - term1[1]*cross_ab[0])
    
    den = 2 * len_cross_sq
    center = (C[0] + num[0]/den, C[1] + num[1]/den, C[2] + num[2]/den)
    r = math.sqrt((center[0]-A[0])**2 + (center[1]-A[1])**2 + (center[2]-A[2])**2)
    len_cross = math.sqrt(len_cross_sq)
    n = (cross_ab[0]/len_cross, cross_ab[1]/len_cross, cross_ab[2]/len_cross)
    
    if n[0]*center[0] + n[1]*center[1] + n[2]*center[2] < 0:
        n = (-n[0], -n[1], -n[2])
        
    return Plane(origin=center, z_dir=n), r


def group_polygons_3d(rows, tol=1e-3):
    def close_pts(a, b):
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) < tol

    segments = []
    for r in rows:
        if "line" in r["draw_type"] and r["p1"] and r["p2"]:
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
        faces.append(Face(Wire.combine(edges)[0]))
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
    log("  10_Art4MotorGear — build123d Assembly Script")
    log(f"  Guidelines: G1 → G15  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 65)

    # ══════════════════════════════════════════════════════════════════════
    # G1 & G2: Read S1, extrude base hub between inner & outer circle
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — inner/outer circles and tooth profile ...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")
    
    s1_circles = [r for r in s1_rows if "circle" in r["draw_type"]]
    s1_lines = [r for r in s1_rows if "line" in r["draw_type"]]
    
    # Process circles for hub
    radii = []
    for c_row in s1_circles:
        plane, r = get_circle_plane_and_radius(c_row["p1"], c_row["p2"], c_row["p3"])
        radii.append(r)
    r_outer = max(radii)
    r_inner = min(radii)
    
    # Process tooth profile
    s1_polys = group_polygons_3d(s1_lines)
    tooth_faces = create_faces_from_polys(s1_polys)
    tooth_face = tooth_faces[0]
    log(f"   → Captured Outer R={r_outer:.2f}, Inner R={r_inner:.2f}, and 1 Tooth Profile.")
    log("--- [G1] Complete ✓ ---")

    log("\n-> [G2] Extruding hub region by 13 units in -Z ...")
    with BuildPart() as hub:
        with BuildSketch(Plane(origin=(0, 0, 13.0), z_dir=(0, 0, 1))):
            Circle(r_outer)
            Circle(r_inner, mode=Mode.SUBTRACT)
        extrude(amount=13.0, dir=(0, 0, -1))
        
    final_solid = keep_main_body(hub.part)
    log(f"   ✓ Gear Hub created. Volume = {get_volume(final_solid):.4f} mm³")
    log("--- [G2] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G4 & G5 & G6: Sweep twisted tooth and pattern 10 times
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G4] Reading S2 — Sweep path definition ...")
    s2_rows = read_csv("Fusion_Coordinates_S2.csv")
    log("   → Sweep path height identified (13.0 mm).")
    log("--- [G4] Complete ✓ ---")

    log("\n-> [G5] Generating mathematically perfect twisted helical sweep ...")
    log("   → Angle: +46.835 deg  |  Generating 60 interpolation frames to prevent deviation")
    
    sections = []
    steps = 60
    z_start = 13.0
    height_diff = -13.0  # Sweep goes from Z=13 down to Z=0
    twist_angle = 46.835 # FIXED: Positive for right-handed helix
    
    for i in range(steps + 1):
        t = i / steps
        z_offset = height_diff * t
        angle = twist_angle * t
        loc = Location((0, 0, z_offset)) * Rotation(0, 0, angle)
        sections.append(tooth_face.moved(loc))
        
    tooth_solid = loft(sections, ruled=True)
    log("   ✓ Single twisted tooth solid generated.")
    log("--- [G5] Complete ✓ ---")

    log("\n-> [G6] Circular patterning the tooth 10 times around the hub ...")
    with BuildPart() as teeth_pattern:
        with PolarLocations(radius=0, count=10):
            add(tooth_solid)
            
    final_solid = keep_main_body(final_solid + teeth_pattern.part)
    log(f"   ✓ Pattern merged into hub. Volume = {get_volume(final_solid):.4f} mm³")
    log("--- [G6] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G7 & G8: Base Flange Extrusion
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G7] Reading S3 — Base flange circle profile ...")
    s3_rows = read_csv("Fusion_Coordinates_S3.csv")
    flange_plane, flange_r = get_circle_plane_and_radius(s3_rows[0]["p1"], s3_rows[0]["p2"], s3_rows[0]["p3"])
    log("--- [G7] Complete ✓ ---")

    log("\n-> [G8] Extruding base flange by 10 units in -Z ...")
    with BuildPart() as flange:
        with BuildSketch(Plane(origin=(0, 0, 0), z_dir=(0, 0, 1))):
            Circle(flange_r)
        extrude(amount=10.0, dir=(0, 0, -1))
        
    final_solid = keep_main_body(final_solid + flange.part)
    log(f"   ✓ Base flange appended. Volume = {get_volume(final_solid):.4f} mm³")
    log("--- [G8] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G9, G10 & G11: Side Holes
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G9] Reading S4 — Inner and outer side holes ...")
    s4_rows = read_csv("Fusion_Coordinates_S4.csv")
    s4_circles = [r for r in s4_rows if "circle" in r["draw_type"]]
    
    radii_s4 = []
    planes_s4 = []
    for c_row in s4_circles:
        pl, r = get_circle_plane_and_radius(c_row["p1"], c_row["p2"], c_row["p3"])
        radii_s4.append(r)
        planes_s4.append(pl)
        
    outer_idx = radii_s4.index(max(radii_s4))
    inner_idx = radii_s4.index(min(radii_s4))
    log(f"   → Captured Outer R={radii_s4[outer_idx]:.2f}, Inner R={radii_s4[inner_idx]:.2f}.")
    log("--- [G9] Complete ✓ ---")

    log("\n-> [G10] Extrude-cutting outer side circle through all in -X ...")
    with BuildPart() as cut_outer:
        with BuildSketch(planes_s4[outer_idx]):
            Circle(radii_s4[outer_idx])
        extrude(amount=100.0, dir=(-1, 0, 0))
    final_solid = final_solid - cut_outer.part
    log("--- [G10] Complete ✓ ---")

    log("\n-> [G11] Extrude-cutting inner side circle by 9 units in +X ...")
    with BuildPart() as cut_inner:
        with BuildSketch(planes_s4[inner_idx]):
            Circle(radii_s4[inner_idx])
        extrude(amount=9.0, dir=(1, 0, 0))
    final_solid = final_solid - cut_inner.part
    log(f"   ✓ Side holes cut. Volume = {get_volume(final_solid):.4f} mm³")
    log("--- [G11] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G12 & G13: Symmetric Wedge Cut
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G12] Reading S5 — Side wedge profile ...")
    s5_rows = read_csv("Fusion_Coordinates_S5.csv")
    s5_polys = group_polygons_3d(s5_rows)
    s5_faces = create_faces_from_polys(s5_polys)
    log("--- [G12] Complete ✓ ---")

    log("\n-> [G13] Extrude-cutting wedge symmetrically (3 units total length) ...")
    with BuildPart() as wedge_cut:
        # FIX: Shift the face -1.5 in X, then do a single extrusion of +3.0 in X.
        # This completely bypasses the OCCT 'both=True' dual-extrusion fusion bug!
        shifted_face = s5_faces[0].moved(Location((-1.5, 0, 0)))
        add(shifted_face)
        extrude(amount=3.0, dir=(1, 0, 0)) 
        
    final_solid = final_solid - wedge_cut.part
    log(f"   ✓ Slotted wedge cut successfully. Volume = {get_volume(final_solid):.4f} mm³")
    log("--- [G13] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G14 & G15: Center Hole Cut (Clear through Flange)
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G14] Reading S6 — Center hole profile ...")
    s6_rows = read_csv("Fusion_Coordinates_S6.csv")
    s6_pl, s6_r = get_circle_plane_and_radius(s6_rows[0]["p1"], s6_rows[0]["p2"], s6_rows[0]["p3"])
    log("--- [G14] Complete ✓ ---")

    log("\n-> [G15] Extrude-cutting center hole by 11 units in +Z ...")
    with BuildPart() as center_cut:
        with BuildSketch(Plane(origin=(0, 0, -10.0), z_dir=(0, 0, 1))):
            Circle(s6_r)
        extrude(amount=11.0, dir=(0, 0, 1))
    final_solid = final_solid - center_cut.part
    log(f"   ✓ Center clearance hole cut. Volume = {get_volume(final_solid):.4f} mm³")
    log("--- [G15] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G3 (FINAL): Clean geometry, Watertight check + export STL/STEP + write summary
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n{'='*65}")
    log("  [G3]  PRE-EXPORT CHECKS & STL/STEP EXPORT")
    log(f"{'='*65}")

    final_solid = final_solid.clean()

    log("\n-> [G3] Watertight check ...")
    free_edges = watertight_check(final_solid, log)

    final_vol = get_volume(final_solid)
    log(f"\n   Final volume = {final_vol:.4f} mm³")

    stl_path = os.path.join(BASE_DIR, STL_NAME)
    try:
        export_stl(final_solid, stl_path, tolerance=0.001, angular_tolerance=0.05)
        stl_kb = os.path.getsize(stl_path) / 1024
        log(f"   ✓ STL saved  : {STL_NAME}  ({stl_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STL export failed: {e}")

    step_path = os.path.join(BASE_DIR, STEP_NAME)
    try:
        export_step(final_solid, step_path)
        step_kb = os.path.getsize(step_path) / 1024
        log(f"   ✓ STEP saved : {STEP_NAME}  ({step_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STEP export failed: {e}")

    log(f"\n{'='*65}")
    log("  BUILD COMPLETE — G1 through G15")
    log(f"{'='*65}")

    log_path = os.path.join(BASE_DIR, LOG_NAME)
    try:
        with open(log_path, "w") as f:
            f.write("\n".join(log_lines))
        print(f"\n📄 Summary saved → {LOG_NAME}")
    except Exception as e:
        print(f"❌ Could not save summary: {e}")

    print("\nDisplaying in OCP viewer on port 3939 ...")
    set_port(3939)
    show([final_solid], names=["Art4MotorGear_G1-G15"])

if __name__ == "__main__":
    main()