"""
9_1_Art4MotorFix_build123d.py

Build the Art4MotorFix part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4MotorFix.stl

Guidelines executed (in logical order):
  G1 : Read S1 — draw closed chamfered rectangle profile and 5 circles in global coordinates.
  G2 : Extrude the enclosed profile (rectangle) EXCEPT the 5 circles by 3 units in +Z.
  G4 : Read S2 — draw profiles yielding two inner rectangles inside an outer rectangle.
  G5 : Extrude the enclosed region EXCEPT the two inner rectangles by 5 units in +Z.
  G6 : Read S3 — draw both circle profiles.
  G7 : Extrude-cut both circles through all in the -X direction.
  G3 : (deferred / final) Clean geometry, watertight check + export STL/STEP + write summary.

Execution order: G1 → G2 → G4 → G5 → G6 → G7 → G3
"""

import os
import csv
import math
from datetime import datetime

from build123d import *
from ocp_vscode import show, set_port

# ── PATHS & NAMING ────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/9_Art4MotorFix"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_START  = 1
G_END    = 7   # full script: G1–G7; G3 is the export step deferred to end
STL_NAME = f"9_Art4MotorFix_G_{G_START}_{G_END}.stl"
STEP_NAME = f"9_Art4MotorFix_G_{G_START}_{G_END}.step"
LOG_NAME = f"9_Art4MotorFix_summary_G_{G_START}_{G_END}.txt"


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
    log("  9_Art4MotorFix — build123d Assembly Script")
    log(f"  Guidelines: G1 → G7  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 65)

    # ══════════════════════════════════════════════════════════════════════
    # G1 & G2: Read S1, extrude chamfered rectangle (except 5 circles) by 3 units in +Z
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — closed chamfered rectangle and 5 circles ...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")

    s1_lines = [r for r in s1_rows if "line" in r["draw_type"]]
    s1_circles = [r for r in s1_rows if "circle" in r["draw_type"]]

    s1_polys = group_polygons_3d(s1_lines)
    s1_faces = create_faces_from_polys(s1_polys)
    
    log(f"   → Captured {len(s1_faces)} outer polygon(s) and {len(s1_circles)} inner circle(s).")
    log("--- [G1] Complete ✓ ---")

    log("\n-> [G2] Extruding enclosed profile except circles by 3 units in +Z ...")
    with BuildPart() as part_g2:
        with BuildSketch(Plane.XY):
            # Base geometry: Outer chamfered rectangle
            add(s1_faces)
            # Subtract geometry: The 5 holes
            for c_row in s1_circles:
                plane, r = get_circle_plane_and_radius(c_row["p1"], c_row["p2"], c_row["p3"])
                # Force local projection to XY sketch plane safely
                with Locations((plane.origin.X, plane.origin.Y)):
                    Circle(r, mode=Mode.SUBTRACT)
        
        extrude(amount=3.0, dir=(0, 0, 1))

    final_solid = keep_main_body(part_g2.part)
    vol = get_volume(final_solid)
    log(f"   ✓ Base plate with 5 holes created. Volume = {vol:.4f} mm³")
    log("--- [G2] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G4 & G5: Read S2, extrude outer region except 2 inner rectangles by 5 units
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G4] Reading S2 — two inner rectangles inside an outer rectangle ...")
    s2_rows = read_csv("Fusion_Coordinates_S2.csv")
    s2_lines = [r for r in s2_rows if "line" in r["draw_type"]]
    
    s2_polys = group_polygons_3d(s2_lines)
    s2_faces = create_faces_from_polys(s2_polys)
    
    # Sort faces by area descending (largest is outer, smaller are inner cuts)
    s2_faces.sort(key=lambda f: f.area, reverse=True)
    
    log(f"   → Captured {len(s2_faces)} rectangular profile(s).")
    log("--- [G4] Complete ✓ ---")

    log("\n-> [G5] Extruding the entire S2 region EXCEPT inner rectangles by 5 units in +Z ...")
    if len(s2_faces) >= 3:
        with BuildPart() as part_g5:
            # We construct this sketch directly on top of the G2 body (Z = 3.0 plane)
            with BuildSketch(Plane(origin=(0, 0, 3.0), z_dir=(0, 0, 1))):
                add(s2_faces[0])  # Add largest bounding rectangle
                for inner_face in s2_faces[1:]:
                    add(inner_face, mode=Mode.SUBTRACT) # Cut out inner ones
                    
            extrude(amount=5.0, dir=(0, 0, 1))
            
        final_solid = keep_main_body(final_solid + part_g5.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Raised wall section with rectangular holes created. Volume = {vol:.4f} mm³")
    else:
        log("   ❌ Error: Did not find at least 3 rectangle profiles in S2.")
    log("--- [G5] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G6 & G7: Read S3, extrude-cut both circles through all in -X direction
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G6] Reading S3 — side circle profiles ...")
    s3_rows = read_csv("Fusion_Coordinates_S3.csv")
    s3_circles = [r for r in s3_rows if "circle" in r["draw_type"]]
    
    log(f"   → Captured {len(s3_circles)} side circle(s).")
    log("--- [G6] Complete ✓ ---")

    log("\n-> [G7] Extrude-cutting S3 circles through all in the -X direction ...")
    if s3_circles:
        with BuildPart() as cut_g7:
            for c_row in s3_circles:
                plane, r = get_circle_plane_and_radius(c_row["p1"], c_row["p2"], c_row["p3"])
                with BuildSketch(plane):
                    Circle(r)
            # Cutting through all explicitly toward negative X
            extrude(amount=100.0, dir=(-1, 0, 0))
            
        final_solid = keep_main_body(final_solid - cut_g7.part)
        vol = get_volume(final_solid)
        log(f"   ✓ Side holes cut successfully. Volume = {vol:.4f} mm³")
    log("--- [G7] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G3 (FINAL): Clean geometry, Watertight check + export STL/STEP + write summary
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n{'='*65}")
    log("  [G3]  PRE-EXPORT CHECKS & STL/STEP EXPORT")
    log(f"{'='*65}")

    # 1. CLEAN THE GEOMETRY
    # Heals topology and removes residual microscopic edges to ensure perfect export
    final_solid = final_solid.clean()

    log("\n-> [G3] Watertight check ...")
    free_edges = watertight_check(final_solid, log)

    final_vol = get_volume(final_solid)
    log(f"\n   Final volume = {final_vol:.4f} mm³")

    # 2. EXPORT HIGH-RES STL
    stl_path = os.path.join(BASE_DIR, STL_NAME)
    try:
        export_stl(final_solid, stl_path, tolerance=0.001, angular_tolerance=0.05)
        stl_kb = os.path.getsize(stl_path) / 1024
        log(f"   ✓ STL saved  : {STL_NAME}  ({stl_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STL export failed: {e}")

    # 3. EXPORT STEP FILE
    step_path = os.path.join(BASE_DIR, STEP_NAME)
    try:
        export_step(final_solid, step_path)
        step_kb = os.path.getsize(step_path) / 1024
        log(f"   ✓ STEP saved : {STEP_NAME}  ({step_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STEP export failed: {e}")

    log(f"\n{'='*65}")
    log("  BUILD COMPLETE — G1 through G7")
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
    show([final_solid], names=["Art4MotorFix_G1-G7"])


if __name__ == "__main__":
    main()