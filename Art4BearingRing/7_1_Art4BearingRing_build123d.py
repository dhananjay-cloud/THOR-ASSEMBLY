"""
7_1_Art4BearingRing_build123d.py

Build the Art4BearingRing part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4BearingRing.stl

Guidelines executed (in logical order):
  G1 : Read S1 — inner circle Ø72 (R=36) and outer circle Ø100 (R=50) at Z=10.
  G2 : Extrude annular region (outer − inner) 10 units in −Z  → base ring body.
  G4 : Read S2 — inner circle Ø80 (R=40) and outer circle Ø100 (R=50) at Z=4.
  G5 : Extrude-cut the G4 annular region 5 units in −Z (top-face recess).
  G6 : Read S3 — four bolt-hole circles (R≈1.275, centres from 3-point data).
  G7 : Extrude-cut the four circles 8 units in +Z (through-holes from bottom).
  G8 : Read S4 — four hexagon profiles (6 lines each, at Z=10).
  G9 : Extrude-cut each hexagon 2.5 units in −Z (hex-head recesses on top).
  G10: Read S5 — groove profile: 1 line + 1 three-point arc at X=36.
  G11: Revolve-cut the G10 profile 360° about the global Z axis (inner groove).
  G12: Read S6 — four circle profiles defined by 3-point data on YZ planes
       (each circle lies at a constant X; all 3 defining points share that X).
  G13: Loft-cut pairwise through the 4 G12 circles to create a linear tapered channel.
  G14: Extrude-cut 12 units in +X using the G12 circle-4 profile (X=−38.076).
  G3 : (deferred / final) Watertight check + export STL + write summary.

Execution order: G1 → G2 → G4 → G5 → G6 → G7 → G8 → G9 → G10 → G11
                 → G12 → G13 → G14 → G3
"""

import os
import csv
import math
from datetime import datetime

from build123d import *
from ocp_vscode import show, set_port

# ── PATHS & NAMING ────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/7_Art4BearingRing"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_START  = 1
G_END    = 14   # full script: G1–G14; G3 is the export step deferred to end
STL_NAME = f"7_Art4BearingRing_G_{G_START}_{G_END}.stl"
LOG_NAME = f"7_Art4BearingRing_summary_G_{G_START}_{G_END}.txt"


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

def circle_centre_radius_from_3pts_xy(p1, p2, p3):
    """
    Circumscribed circle through three XY-plane points (Z is ignored).
    Returns ((cx, cy), radius).
    """
    ax, ay = p1[0], p1[1]
    bx, by = p2[0], p2[1]
    cx, cy = p3[0], p3[1]
    D = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(D) < 1e-12:
        raise ValueError("Points are collinear — cannot compute circle.")
    ux = ((ax**2 + ay**2) * (by - cy) +
          (bx**2 + by**2) * (cy - ay) +
          (cx**2 + cy**2) * (ay - by)) / D
    uy = ((ax**2 + ay**2) * (cx - bx) +
          (bx**2 + by**2) * (ax - cx) +
          (cx**2 + cy**2) * (bx - ax)) / D
    r = math.sqrt((ax - ux) ** 2 + (ay - uy) ** 2)
    return (ux, uy), r


def circle_centre_radius_from_3pts_yz(p1, p2, p3):
    """
    Circumscribed circle through three 3-D points that share the same X value.
    The circle lies on the YZ plane at that constant X.

    Reuses circle_centre_radius_from_3pts_xy by mapping:
        axis-1 → Y,  axis-2 → Z

    Returns (x_val, (cy, cz), radius).
    """
    x_val = p1[0]   # all three points share the same X
    (cy, cz), r = circle_centre_radius_from_3pts_xy(
        (p1[1], p1[2]),
        (p2[1], p2[2]),
        (p3[1], p3[2]),
    )
    return x_val, (cy, cz), r


def group_hexagons(rows):
    """
    Chain the line segments from S4 into closed hexagonal polygons.
    Returns a list of polygons; each polygon is a list of (x, y) 2-D vertices
    in traversal order (the repeated closing vertex is dropped).
    """
    tol = 1e-3

    def close_pts(a, b):
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2) < tol

    segments = []
    for r in rows:
        if r["draw_type"] == "line" and r["p1"] and r["p2"]:
            a = (round(r["p1"][0], 4), round(r["p1"][1], 4))
            b = (round(r["p2"][0], 4), round(r["p2"][1], 4))
            segments.append((a, b))

    used  = [False] * len(segments)
    polys = []

    for start_idx, (sa, sb) in enumerate(segments):
        if used[start_idx]:
            continue
        chain    = [sa, sb]
        used_tmp = [False] * len(segments)
        used_tmp[start_idx] = True

        for _ in range(5):
            current_end = chain[-1]
            found = False
            for j, (ja, jb) in enumerate(segments):
                if used_tmp[j] or used[j]:
                    continue
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
            if close_pts(chain[-1], chain[0]) and len(chain) == 7:
                for j, flag in enumerate(used_tmp):
                    if flag:
                        used[j] = True
                polys.append(chain[:-1])
                break

    return polys


def watertight_check(solid, log_fn):
    """
    Use OCC sewing to count free edges.  0 free edges → watertight.
    Returns the free-edge count.
    """
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


def get_volume(solid):
    v = solid.volume
    return v() if callable(v) else v


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    log_lines = []

    def log(msg=""):
        print(msg)
        log_lines.append(msg)

    log("=" * 65)
    log("  7_Art4BearingRing — build123d Assembly Script")
    log(f"  Guidelines: G1 → G14  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 65)

    # ══════════════════════════════════════════════════════════════════════
    # G1: Read S1 — inner circle Ø72 (R=36) and outer circle Ø100 (R=50)
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — inner Ø72 and outer Ø100 circles ...")

    s1_rows = read_csv("Fusion_Coordinates_S1.csv")

    circle_params = []
    for row in s1_rows:
        if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
            (cx, cy), r = circle_centre_radius_from_3pts_xy(row["p1"], row["p2"], row["p3"])
            z_level = row["p1"][2]
            circle_params.append({"cx": cx, "cy": cy, "r": r, "z": z_level})
            log(f"   S1 circle → centre=({cx:.3f},{cy:.3f}), R={r:.4f}, Z={z_level}")

    if len(circle_params) < 2:
        log("   ❌ Could not read two circles from S1. Aborting.")
        return

    circle_params.sort(key=lambda c: c["r"])
    r_inner = circle_params[0]["r"]
    r_outer = circle_params[1]["r"]
    z_top   = circle_params[0]["z"]

    log(f"   → Inner R={r_inner:.4f}  Outer R={r_outer:.4f}  Z_top={z_top}")
    log("--- [G1] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G2: Extrude annular region (outer − inner) 10 units in −Z
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G2] Extruding annular ring (Ø{2*r_inner:.1f} bore / Ø{2*r_outer:.1f} OD) "
        f"by 10 units in −Z ...")

    with BuildPart() as part:
        with BuildSketch(Plane.XY.offset(z_top)):
            Circle(r_outer)
            Circle(r_inner, mode=Mode.SUBTRACT)
        extrude(amount=10.0, dir=(0, 0, -1))

    final_solid = part.part
    vol = get_volume(final_solid)
    log(f"   ✓ Base ring created. Volume = {vol:.4f} mm³")
    log("--- [G2] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G4: Read S2 — inner circle Ø80 (R=40) and outer circle Ø100 (R=50)
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G4] Reading S2 — inner Ø80 and outer Ø100 circles for recess ...")

    s2_rows = read_csv("Fusion_Coordinates_S2.csv")

    recess_params = []
    for row in s2_rows:
        if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
            (cx, cy), r = circle_centre_radius_from_3pts_xy(row["p1"], row["p2"], row["p3"])
            z_level = row["p1"][2]
            recess_params.append({"cx": cx, "cy": cy, "r": r, "z": z_level})
            log(f"   S2 circle → centre=({cx:.3f},{cy:.3f}), R={r:.4f}, Z={z_level}")

    if len(recess_params) < 2:
        log("   ⚠️  Could not read two circles from S2. Skipping G4/G5.")
    else:
        recess_params.sort(key=lambda c: c["r"])
        r_recess_inner = recess_params[0]["r"]
        r_recess_outer = recess_params[1]["r"]
        z_recess       = recess_params[0]["z"]
        log(f"   → Inner R={r_recess_inner:.4f}  Outer R={r_recess_outer:.4f}  Z={z_recess}")
        log("--- [G4] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G5: Extrude-cut the G4 annular region 5 units in −Z
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G5] Extrude-cutting recess annulus (Ø{2*r_recess_inner:.1f}–Ø{2*r_recess_outer:.1f}) "
            f"5 units in −Z from Z={z_recess} ...")

        with BuildPart() as cut_g5:
            with BuildSketch(Plane.XY.offset(z_recess)):
                Circle(r_recess_outer)
                Circle(r_recess_inner, mode=Mode.SUBTRACT)
            extrude(amount=5.0, dir=(0, 0, -1))

        final_solid = final_solid - cut_g5.part
        vol = get_volume(final_solid)
        log(f"   ✓ Recess cut done. Volume = {vol:.4f} mm³")
        log("--- [G5] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G6: Read S3 — four bolt-hole circles
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G6] Reading S3 — four bolt-hole circles ...")

    s3_rows = read_csv("Fusion_Coordinates_S3.csv")

    hole_params = []
    for row in s3_rows:
        if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
            (cx, cy), r = circle_centre_radius_from_3pts_xy(row["p1"], row["p2"], row["p3"])
            z_level = row["p1"][2]
            hole_params.append({"cx": cx, "cy": cy, "r": r, "z": z_level})
            log(f"   S3 hole → centre=({cx:.3f},{cy:.3f}), R={r:.4f}, Z={z_level}")

    if not hole_params:
        log("   ⚠️  No hole circles found in S3. Skipping G6/G7.")
    else:
        log(f"   → {len(hole_params)} hole(s) detected.")
        log("--- [G6] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G7: Extrude-cut all four circles 8 units in +Z
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G7] Extrude-cutting {len(hole_params)} bolt holes 8 units in +Z ...")

        with BuildPart() as cut_g7:
            with BuildSketch(Plane.XY.offset(hole_params[0]["z"])):
                for hp in hole_params:
                    with Locations((hp["cx"], hp["cy"])):
                        Circle(hp["r"])
            extrude(amount=8.0, dir=(0, 0, 1))

        final_solid = final_solid - cut_g7.part
        vol = get_volume(final_solid)
        log(f"   ✓ Bolt holes cut. Volume = {vol:.4f} mm³")
        log("--- [G7] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G8: Read S4 — four hexagon profiles (6 lines each, at Z=10)
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G8] Reading S4 — four hexagon profiles ...")

    s4_rows   = read_csv("Fusion_Coordinates_S4.csv")
    hex_polys = group_hexagons(s4_rows)
    z_hex     = s4_rows[0]["p1"][2] if s4_rows else 10.0

    for i, poly in enumerate(hex_polys):
        log(f"   Hexagon {i+1}: {len(poly)} vertices at Z={z_hex}  "
            f"| first vertex = {poly[0]}")

    if not hex_polys:
        log("   ⚠️  No hexagons found in S4. Skipping G8/G9.")
    else:
        log(f"   → {len(hex_polys)} hexagon(s) detected.")
        log("--- [G8] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G9: Extrude-cut each hexagon 2.5 units in −Z
        # ══════════════════════════════════════════════════════════════════════
        log(f"\n-> [G9] Extrude-cutting {len(hex_polys)} hexagon recesses 2.5 units in −Z ...")

        with BuildPart() as cut_g9:
            with BuildSketch(Plane.XY.offset(z_hex)):
                for poly in hex_polys:
                    Polygon([(v[0], v[1]) for v in poly], align=None)
            extrude(amount=2.5, dir=(0, 0, -1))

        final_solid = final_solid - cut_g9.part
        vol = get_volume(final_solid)
        log(f"   ✓ Hex recesses cut. Volume = {vol:.4f} mm³")
        log("--- [G9] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G10: Read S5 — groove profile (1 straight line + 1 three-point arc)
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G10] Reading S5 — groove profile (line + arc) ...")

    s5_rows     = read_csv("Fusion_Coordinates_S5.csv")
    groove_line = None
    groove_arc  = None
    for row in s5_rows:
        if row["draw_type"] == "line" and row["p1"] and row["p2"]:
            groove_line = row
        elif "3_point_arc" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
            groove_arc  = row

    if groove_line is None or groove_arc is None:
        log("   ⚠️  Could not read line/arc from S5. Skipping G10/G11.")
    else:
        line_A = (groove_line["p1"][0], groove_line["p1"][2])
        line_B = (groove_line["p2"][0], groove_line["p2"][2])
        arc_s  = (groove_arc["p1"][0],  groove_arc["p1"][2])
        arc_m  = (groove_arc["p2"][0],  groove_arc["p2"][2])
        arc_e  = (groove_arc["p3"][0],  groove_arc["p3"][2])

        log(f"   Line:  A={line_A} → B={line_B}")
        log(f"   Arc :  {arc_s} --({arc_m})--> {arc_e}")
        log("--- [G10] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G11: Revolve-cut the G10 profile 360° about the global Z axis
        # ══════════════════════════════════════════════════════════════════════
        log("\n-> [G11] Revolve-cutting groove profile 360° about Z axis ...")

        with BuildPart() as cut_g11:
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    Line((line_A[0], line_A[1]), (line_B[0], line_B[1]))
                    ThreePointArc(
                        (arc_s[0], arc_s[1]),
                        (arc_m[0], arc_m[1]),
                        (arc_e[0], arc_e[1])
                    )
                make_face()
            revolve(axis=Axis.Z, revolution_arc=360)

        final_solid = final_solid - cut_g11.part
        vol = get_volume(final_solid)
        log(f"   ✓ Groove revolve-cut done. Volume = {vol:.4f} mm³")
        log("--- [G11] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G12: Read S6 — four circle profiles defined by 3-point data on YZ planes.
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G12] Reading S6 — four circle profiles on YZ planes ...")

    s6_rows          = read_csv("Fusion_Coordinates_S6.csv")
    s6_circle_params = []

    for row in s6_rows:
        if "3_point_circle" in row["draw_type"] and row["p1"] and row["p2"] and row["p3"]:
            x_val, (cy, cz), r = circle_centre_radius_from_3pts_yz(
                row["p1"], row["p2"], row["p3"]
            )
            sketch_plane = Plane(
                origin=(x_val, cy, cz),
                x_dir=(0, 1, 0),    # local X → global Y
                z_dir=(1, 0, 0),    # normal  → global +X
            )
            s6_circle_params.append({
                "x_val":        x_val,
                "cy":           cy,
                "cz":           cz,
                "r":            r,
                "sketch_plane": sketch_plane,
            })
            log(f"   S6 circle → X={x_val:.3f}, "
                f"centre_YZ=({cy:.4f}, {cz:.4f}), R={r:.4f}")

    if len(s6_circle_params) != 4:
        log(f"   ⚠️  Expected 4 circles from S6, got {len(s6_circle_params)}. "
            f"Skipping G12/G13/G14.")
        s6_circle_params = []
    else:
        log(f"   → {len(s6_circle_params)} circle profiles built.")
        log("--- [G12] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G13: Loft-cut pairwise through the 4 G12 circle profiles.
    #      Perform operation one by one (1->2, then 2->3, then 3->4) 
    #      to maintain a linear cut profile instead of a curved spline.
    # ══════════════════════════════════════════════════════════════════════
    if s6_circle_params:
        log("\n-> [G13] Loft-cutting pairwise (linear profile) through S6 circles ...")

        for i in range(len(s6_circle_params) - 1):
            cp_start = s6_circle_params[i]
            cp_end   = s6_circle_params[i+1]
            
            log(f"   Lofting segment {i+1}: X={cp_start['x_val']:.3f} to X={cp_end['x_val']:.3f}")
            
            with BuildPart() as cut_segment:
                with BuildSketch(cp_start["sketch_plane"]):
                    Circle(cp_start["r"])
                with BuildSketch(cp_end["sketch_plane"]):
                    Circle(cp_end["r"])
                loft()

            final_solid = final_solid - cut_segment.part
            
        vol = get_volume(final_solid)
        log(f"   ✓ Pairwise loft cuts completed. Volume = {vol:.4f} mm³")
        log("--- [G13] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G14: Extrude-cut 12 units in +X using circle-4 profile (X = −38.076).
    # ══════════════════════════════════════════════════════════════════════
    if s6_circle_params:
        cp4 = s6_circle_params[3]   # circle 4 — X = −38.076
        log(f"\n-> [G14] Extrude-cutting 12 units in +X using circle-4 profile "
            f"(X={cp4['x_val']:.3f}) ...")

        with BuildPart() as cut_g14:
            with BuildSketch(cp4["sketch_plane"]):
                Circle(cp4["r"])
            # sketch_plane normal = global +X → amount=+12 cuts in +X direction
            extrude(amount=12, dir=(1, 0, 0))

        final_solid = final_solid - cut_g14.part
        vol = get_volume(final_solid)
        log(f"   ✓ Extrude cut: 12 mm in +X from X={cp4['x_val']:.3f} "
            f"| centre_YZ=({cp4['cy']:.4f}, {cp4['cz']:.4f}), R={cp4['r']:.4f} mm "
            f"| Volume = {vol:.4f} mm³")
        log("--- [G14] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G3 (FINAL): Watertight check + export STL + write summary
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n{'='*65}")
    log("  [G3]  PRE-EXPORT CHECKS & STL EXPORT")
    log(f"{'='*65}")

    log("\n-> [G3] Watertight check ...")
    free_edges = watertight_check(final_solid, log)

    final_vol = get_volume(final_solid)
    log(f"\n   Final volume = {final_vol:.4f} mm³")

    stl_path = os.path.join(BASE_DIR, STL_NAME)
    try:
        export_stl(final_solid, stl_path, tolerance=0.005, angular_tolerance=0.05)
        stl_kb = os.path.getsize(stl_path) / 1024
        log(f"   ✓ STL saved  : {STL_NAME}  ({stl_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STL export failed: {e}")

    log(f"\n{'='*65}")
    log("  BUILD COMPLETE — G1 through G14")
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
    show([final_solid], names=["Art4BearingRing_G1-G14"])


if __name__ == "__main__":
    main()