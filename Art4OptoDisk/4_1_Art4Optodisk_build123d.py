"""
4_1_Art4Optodisk_build123d.py

Build the Art4Optodisk part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4Optodisk.stl

  G1:  Read S1 — two 3-point circles on XY plane at Z=0.
       Fit circumcircles: inner R≈21, outer R≈30.2, both centered at origin.
       Build annular (ring) face between inner and outer circles.
  G2:  Extrude annular profile 15 units in +Z direction.
  G3:  Export STL + summary log (deferred to end of script).
  G4:  Read S2 — two 3-point circles at Z=5.
       Inner R≈21, outer R≈29.2 → annular groove region.
  G5:  Extrude-cut annular groove from G4 by 10 units in +Z.
  G6:  Read S3 — two circles at different Z levels, both centered at (0, 24):
       Circle 1: R≈2.95 at Z=5 (wider countersink top)
       Circle 2: R≈1.7  at Z=2 (narrower through-hole)
  G7:  Extrude-cut circle at Z=5 (R=2.95) by 3 units in −Z.
  G8:  Extrude-cut circle at Z=2 (R=1.7) by 2 units in −Z.
  G9:  Apply circular pattern to G7+G8 cut features — 4 copies at 90° intervals.
       Creates 4 countersink screw holes around the ring.
  G10: Read S4 — 4 corner points defining a rectangle at X≈30.196.
       Rectangle: Y=[-0.5, 0.5], Z=[5, 15] on the YZ plane.
  G11: Extrude-cut rectangle 2 units in −X direction to make a slot.
       Face starts 0.5 units outside the outer surface to fully clear
       the curved wall and eliminate any semicircular residual artifact.
  G12: Read S5 — one 3-point circle at Z=5.
       Fit circumcircle: R≈29.2, centered at origin.
       Build circle face on XY plane at Z=5.
  G13: Extrude-cut circle profile from G12 by 16 units in +Z.
  G3 (Final): Watertight check, volume report, export STL + summary.
"""

import os
import csv
import math
from build123d import *
from ocp_vscode import show, set_port
from datetime import datetime

# ── PATHS & CONFIG ───────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/4_Art4Optodisk"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_RANGE   = "1_13"
STL_NAME  = f"4_Art4Optodisk_G_{G_RANGE}.stl"
LOG_NAME  = f"4_Art4Optodisk_summary_G_{G_RANGE}.txt"

EXTRUDE_DEPTH_G2  = 15.0   # G2:  S1 annular ring extrude in +Z
EXTRUDE_DEPTH_G5  = 10.0   # G5:  S2 annular groove cut in +Z
EXTRUDE_DEPTH_G7  = 3.0    # G7:  S3 countersink top cut in −Z
EXTRUDE_DEPTH_G8  = 2.0    # G8:  S3 through-hole cut in −Z
EXTRUDE_DEPTH_G11 = 2.0    # G11: S4 rectangle slot cut in −X (increased from 1.0 to 2.0)
EXTRUDE_DEPTH_G13 = 16.0   # G13: S5 circle cut in −Z
G11_OVERHANG      = 0.5    # G11: extra offset so face starts outside the curved wall
CIRCULAR_PATTERN_COUNT = 4  # G9:  4 countersink holes

# ════════════════════════════════════════════════════════════════════════════
# DATA PARSING
# ════════════════════════════════════════════════════════════════════════════

def read_csv(filename):
    """Read a Fusion coordinate CSV and return parsed rows."""
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
    """Compute circumcircle center and radius from 3 points in 2D (XY)."""
    ax, ay = p1[0], p1[1]
    bx, by = p2[0], p2[1]
    cx, cy = p3[0], p3[1]
    D = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(D) < 1e-12:
        raise ValueError("Collinear points — cannot fit circle.")
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / D
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / D
    return (ux, uy), math.sqrt((ax - ux)**2 + (ay - uy)**2)


def cut_solid_with_tool(main_shape, tool_shape):
    """Boolean cut using OCP."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    cutter = BRepAlgoAPI_Cut()
    args = TopTools_ListOfShape(); args.Append(main_shape)
    tools = TopTools_ListOfShape(); tools.Append(tool_shape)
    cutter.SetArguments(args); cutter.SetTools(tools)
    cutter.SetFuzzyValue(1e-3); cutter.Build()
    return cutter.Shape() if cutter.IsDone() else main_shape


def extract_largest_solid(shape):
    """Extract the largest solid from a compound shape."""
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    solids = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solids.append(Solid(explorer.Current())); explorer.Next()
    if not solids:
        return None
    def get_vol(s):
        v = s.volume; return v() if callable(v) else v
    return max(solids, key=get_vol)


def watertight_check(solid, log_fn):
    """Check if a solid's mesh is watertight (no free edges)."""
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
    log("  4_Art4Optodisk — build123d Assembly Script")
    log(f"  Guidelines: G1 → G13  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # ══════════════════════════════════════════════════════════════════════
    # G1: Read S1 — two 3-point circles on XY plane at Z=0
    #     Inner R≈21, Outer R≈30.2 → annular ring face
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — two 3-point circles at Z=0...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")
    if not s1_rows:
        log("   ❌ No data in S1. Aborting."); return

    s1_circles = []
    for r in s1_rows:
        if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
            z_val = r["p1"][2]
            s1_circles.append({
                "center": center, "radius": radius, "z": z_val,
                "label": r["draw_type"],
            })
            log(f"   ✓ {r['draw_type']}: center=({center[0]:.4f}, {center[1]:.4f}), "
                f"R={radius:.4f}, Z={z_val}")

    if len(s1_circles) < 2:
        log(f"   ❌ Expected 2 circles, got {len(s1_circles)}. Aborting."); return

    s1_circles.sort(key=lambda c: c["radius"])
    s1_inner, s1_outer = s1_circles[0], s1_circles[1]
    z_plane_s1 = s1_outer["z"]
    log(f"\n   Inner R={s1_inner['radius']:.4f}  Outer R={s1_outer['radius']:.4f}  Z={z_plane_s1}")

    with BuildPart() as part_builder:
        # Annular ring: outer circle minus inner circle
        with BuildSketch(Plane(origin=(0, 0, z_plane_s1), z_dir=(0, 0, 1))):
            with Locations([(s1_outer["center"][0], s1_outer["center"][1])]):
                Circle(s1_outer["radius"])
            with Locations([(s1_inner["center"][0], s1_inner["center"][1])]):
                Circle(s1_inner["radius"], mode=Mode.SUBTRACT)

        log(f"   ✓ Annular sketch: outer R={s1_outer['radius']:.4f}, inner R={s1_inner['radius']:.4f}")
        log("--- [G1] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G2: Extrude annular profile 15 units in +Z
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G2] Extruding annular profile {EXTRUDE_DEPTH_G2} in +Z...")
        extrude(amount=EXTRUDE_DEPTH_G2)
        vol = part_builder.part.volume
        vol_val = vol() if callable(vol) else vol
        log(f"   ✓ Volume after G2 = {vol_val:.4f} mm³")
        log("--- [G2] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G4: Read S2 — two 3-point circles at Z=5
        #     Inner R≈21, Outer R≈29.2 → annular groove
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G4] Reading S2 — two 3-point circles at Z=5...")
        s2_rows = read_csv("Fusion_Coordinates_S2.csv")

        s2_circles = []
        if not s2_rows:
            log("   ❌ No data in S2. Skipping G4-G5.")
        else:
            for r in s2_rows:
                if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
                    center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                    z_val = r["p1"][2]
                    s2_circles.append({
                        "center": center, "radius": radius, "z": z_val,
                        "label": r["draw_type"],
                    })
                    log(f"   ✓ {r['draw_type']}: center=({center[0]:.4f}, {center[1]:.4f}), "
                        f"R={radius:.4f}, Z={z_val}")

            s2_circles.sort(key=lambda c: c["radius"])
            s2_inner, s2_outer = s2_circles[0], s2_circles[1]
            z_plane_s2 = s2_outer["z"]
            log(f"\n   Inner R={s2_inner['radius']:.4f}  Outer R={s2_outer['radius']:.4f}  Z={z_plane_s2}")
            log("--- [G4] Complete ✓ ---")

            # ══════════════════════════════════════════════════════════════
            # G5: Extrude-cut annular groove by 10 units in +Z
            # ══════════════════════════════════════════════════════════════
            log(f"\n-> [G5] Extrude-cutting annular groove by {EXTRUDE_DEPTH_G5} in +Z...")

            with BuildSketch(Plane(origin=(0, 0, z_plane_s2), z_dir=(0, 0, 1))):
                with Locations([(s2_outer["center"][0], s2_outer["center"][1])]):
                    Circle(s2_outer["radius"])
                with Locations([(s2_inner["center"][0], s2_inner["center"][1])]):
                    Circle(s2_inner["radius"], mode=Mode.SUBTRACT)
            extrude(amount=EXTRUDE_DEPTH_G5, mode=Mode.SUBTRACT)

            vol = part_builder.part.volume
            vol_val = vol() if callable(vol) else vol
            log(f"   ✓ Volume after G5 = {vol_val:.4f} mm³")
            log("--- [G5] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G6: Read S3 — two circles at different Z levels
        #     Circle 1: R≈2.95 at Z=5 (countersink top, wider)
        #     Circle 2: R≈1.70 at Z=2 (through-hole, narrower)
        #     Both centered at approximately (0, 24) in XY
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G6] Reading S3 — countersink hole profiles...")
        s3_rows = read_csv("Fusion_Coordinates_S3.csv")

        s3_circle_z5 = None  # countersink top (wider, Z=5)
        s3_circle_z2 = None  # through-hole (narrower, Z=2)

        if not s3_rows:
            log("   ❌ No data in S3. Skipping G6-G9.")
        else:
            for r in s3_rows:
                if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
                    center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                    z_val = r["p1"][2]
                    circ_info = {
                        "center": center, "radius": radius, "z": z_val,
                        "label": r["draw_type"],
                    }
                    log(f"   ✓ {r['draw_type']}: center=({center[0]:.4f}, {center[1]:.4f}), "
                        f"R={radius:.4f}, Z={z_val}")

                    if abs(z_val - 5.0) < 0.1:
                        s3_circle_z5 = circ_info
                    elif abs(z_val - 2.0) < 0.1:
                        s3_circle_z2 = circ_info

            log("--- [G6] Complete ✓ ---")

            # ══════════════════════════════════════════════════════════════
            # G7: Extrude-cut countersink top (Z=5, R≈2.95) by 3 in −Z
            # ══════════════════════════════════════════════════════════════
            if s3_circle_z5:
                log(f"\n-> [G7] Extrude-cutting countersink top (R={s3_circle_z5['radius']:.4f}) "
                    f"by {EXTRUDE_DEPTH_G7} in −Z...")

                cx, cy = s3_circle_z5["center"]
                z_val = s3_circle_z5["z"]

                with BuildSketch(Plane(origin=(0, 0, z_val), z_dir=(0, 0, 1))):
                    with Locations([(cx, cy)]):
                        Circle(s3_circle_z5["radius"])
                extrude(amount=-EXTRUDE_DEPTH_G7, mode=Mode.SUBTRACT)

                vol = part_builder.part.volume
                vol_val = vol() if callable(vol) else vol
                log(f"   ✓ Volume after G7 = {vol_val:.4f} mm³")
                log("--- [G7] Complete ✓ ---")
            else:
                log("   ⚠️  No Z=5 circle found in S3. Skipping G7.")

            # ══════════════════════════════════════════════════════════════
            # G8: Extrude-cut through-hole (Z=2, R≈1.7) by 2 in −Z
            # ══════════════════════════════════════════════════════════════
            if s3_circle_z2:
                log(f"\n-> [G8] Extrude-cutting through-hole (R={s3_circle_z2['radius']:.4f}) "
                    f"by {EXTRUDE_DEPTH_G8} in −Z...")

                cx, cy = s3_circle_z2["center"]
                z_val = s3_circle_z2["z"]

                with BuildSketch(Plane(origin=(0, 0, z_val), z_dir=(0, 0, 1))):
                    with Locations([(cx, cy)]):
                        Circle(s3_circle_z2["radius"])
                extrude(amount=-EXTRUDE_DEPTH_G8, mode=Mode.SUBTRACT)

                vol = part_builder.part.volume
                vol_val = vol() if callable(vol) else vol
                log(f"   ✓ Volume after G8 = {vol_val:.4f} mm³")
                log("--- [G8] Complete ✓ ---")
            else:
                log("   ⚠️  No Z=2 circle found in S3. Skipping G8.")

            # ══════════════════════════════════════════════════════════════
            # G9: Circular pattern — replicate G7+G8 countersink holes
            #     4 copies at 90° intervals around Z axis (origin)
            #
            #     Strategy: We already cut the first hole at ~(0, 24).
            #     Now we cut 3 more at 90°, 180°, 270° by rotating the
            #     hole center coordinates and repeating the cut operations.
            # ══════════════════════════════════════════════════════════════
            if s3_circle_z5 and s3_circle_z2:
                log(f"\n-> [G9] Applying circular pattern — {CIRCULAR_PATTERN_COUNT} "
                    f"countersink holes at 90° intervals...")

                # Original hole center
                cx_orig, cy_orig = s3_circle_z5["center"]
                # Distance from origin (should be ~24)
                hole_dist = math.sqrt(cx_orig**2 + cy_orig**2)
                # Angle of original hole
                base_angle = math.atan2(cy_orig, cx_orig)

                log(f"   Original hole at ({cx_orig:.3f}, {cy_orig:.3f}), "
                    f"dist={hole_dist:.3f}, angle={math.degrees(base_angle):.1f}°")

                # Cut 3 more copies at 90° intervals (skip the first — already cut)
                for copy_idx in range(1, CIRCULAR_PATTERN_COUNT):
                    angle = base_angle + copy_idx * (2 * math.pi / CIRCULAR_PATTERN_COUNT)
                    cx_rot = hole_dist * math.cos(angle)
                    cy_rot = hole_dist * math.sin(angle)

                    log(f"   Copy {copy_idx+1}: angle={math.degrees(angle):.1f}°, "
                        f"center=({cx_rot:.3f}, {cy_rot:.3f})")

                    # G7 copy: countersink top (Z=5, larger radius)
                    z5 = s3_circle_z5["z"]
                    r5 = s3_circle_z5["radius"]
                    with BuildSketch(Plane(origin=(0, 0, z5), z_dir=(0, 0, 1))):
                        with Locations([(cx_rot, cy_rot)]):
                            Circle(r5)
                    extrude(amount=-EXTRUDE_DEPTH_G7, mode=Mode.SUBTRACT)

                    # G8 copy: through-hole (Z=2, smaller radius)
                    z2 = s3_circle_z2["z"]
                    r2 = s3_circle_z2["radius"]
                    with BuildSketch(Plane(origin=(0, 0, z2), z_dir=(0, 0, 1))):
                        with Locations([(cx_rot, cy_rot)]):
                            Circle(r2)
                    extrude(amount=-EXTRUDE_DEPTH_G8, mode=Mode.SUBTRACT)

                    vol = part_builder.part.volume
                    vol_val = vol() if callable(vol) else vol
                    log(f"   ✓ Copy {copy_idx+1} cut. Volume = {vol_val:.4f} mm³")

                vol = part_builder.part.volume
                vol_val = vol() if callable(vol) else vol
                log(f"   Volume after G9 = {vol_val:.4f} mm³")
                log("--- [G9] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G10: Read S4 — 4 corner points defining a rectangle
        #      All at X≈30.196, Y=[-0.5, 0.5], Z=[5, 15]
        #      This is a rectangle on the YZ plane at the outer edge.
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G10] Reading S4 — 4 corner points for rectangle...")
        s4_rows = read_csv("Fusion_Coordinates_S4.csv")

        rect_pts = []
        if not s4_rows:
            log("   ❌ No data in S4. Skipping G10-G11.")
        else:
            for r in s4_rows:
                if r["draw_type"] == "point":
                    rect_pts.append(r["p1"])
                    log(f"   ✓ Point: ({r['p1'][0]:.3f}, {r['p1'][1]:.3f}, {r['p1'][2]:.3f})")

            if len(rect_pts) == 4:
                # Extract rectangle dimensions
                x_val = rect_pts[0][0]
                ys = [p[1] for p in rect_pts]
                zs = [p[2] for p in rect_pts]
                y_min, y_max = min(ys), max(ys)
                z_min, z_max = min(zs), max(zs)

                log(f"\n   Rectangle at X={x_val:.3f}")
                log(f"   Y: [{y_min:.3f}, {y_max:.3f}], Z: [{z_min:.3f}, {z_max:.3f}]")
                log("--- [G10] Complete ✓ ---")

                # ══════════════════════════════════════════════════════════
                # G11: Extrude-cut rectangle 2 units in −X to make slot.
                #
                #      FIX vs original script:
                #        1. Depth increased from 1.0 → 2.0 mm so the cut
                #           fully penetrates the outer wall thickness.
                #        2. The cut face is started G11_OVERHANG (0.5 mm)
                #           OUTSIDE the body (x_start = x_val + 0.5) and
                #           the prism length is extended by the same amount,
                #           so the tool enters from outside the curved wall.
                #           This eliminates the semicircular residual surface
                #           that appeared when the face was flush with x_val.
                # ══════════════════════════════════════════════════════════
                log(f"\n-> [G11] Extrude-cutting rectangle by {EXTRUDE_DEPTH_G11} in −X "
                    f"(face offset +{G11_OVERHANG} outside body)...")

                from OCP.gp import gp_Pnt, gp_Vec
                from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                                 BRepBuilderAPI_MakeWire,
                                                 BRepBuilderAPI_MakeFace)
                from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

                # Start the rectangle face slightly outside the outer surface
                # so the boolean tool fully intersects the curved wall.
                x_start = x_val + G11_OVERHANG

                corners = [
                    gp_Pnt(x_start, y_min, z_min),
                    gp_Pnt(x_start, y_max, z_min),
                    gp_Pnt(x_start, y_max, z_max),
                    gp_Pnt(x_start, y_min, z_max),
                ]
                wire_maker = BRepBuilderAPI_MakeWire()
                for i in range(4):
                    edge = BRepBuilderAPI_MakeEdge(corners[i], corners[(i+1) % 4]).Edge()
                    wire_maker.Add(edge)

                if wire_maker.IsDone():
                    face = BRepBuilderAPI_MakeFace(wire_maker.Wire())
                    if face.IsDone():
                        # Total prism length = desired depth + overhang so the
                        # far face of the prism sits at x_val - EXTRUDE_DEPTH_G11
                        total_cut = EXTRUDE_DEPTH_G11 + G11_OVERHANG
                        prism_vec = gp_Vec(-total_cut, 0, 0)
                        prism = BRepPrimAPI_MakePrism(face.Face(), prism_vec)

                        if prism.IsDone():
                            result_shape = cut_solid_with_tool(
                                part_builder.part.wrapped, prism.Shape()
                            )
                            extracted = extract_largest_solid(result_shape)
                            if extracted:
                                part_builder._part = extracted
                                vol = extracted.volume
                                vol_val = vol() if callable(vol) else vol
                                log(f"   ✓ Rectangle slot cut. Volume = {vol_val:.4f} mm³")
                            else:
                                log("   ⚠️  No solid after rectangle cut.")
                        else:
                            log("   ❌ Rectangle prism extrusion failed.")
                    else:
                        log("   ❌ Rectangle face creation failed.")
                else:
                    log("   ❌ Rectangle wire creation failed.")

                vol = part_builder.part.volume
                vol_val = vol() if callable(vol) else vol
                log(f"   Volume after G11 = {vol_val:.4f} mm³")
                log("--- [G11] Complete ✓ ---")
            else:
                log(f"   ⚠️  Expected 4 points, got {len(rect_pts)}. Skipping G10-G11.")

        # ══════════════════════════════════════════════════════════════════
        # G12: Read S5 — one 3-point circle at Z=5
        #      Fit circumcircle: R≈29.2, centered at origin.
        #      Build circle face on XY plane at Z=5.
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G12] Reading S5 — single 3-point circle at Z=5...")
        s5_rows = read_csv("Fusion_Coordinates_S5.csv")

        s5_circle = None
        if not s5_rows:
            log("   ❌ No data in S5. Skipping G12-G13.")
        else:
            for r in s5_rows:
                if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
                    center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                    z_val = r["p1"][2]
                    s5_circle = {
                        "center": center, "radius": radius, "z": z_val,
                        "label": r["draw_type"],
                    }
                    log(f"   ✓ {r['draw_type']}: center=({center[0]:.4f}, {center[1]:.4f}), "
                        f"R={radius:.4f}, Z={z_val}")

            if s5_circle is None:
                log("   ❌ No 3-point circle found in S5. Skipping G12-G13.")
            else:
                log("--- [G12] Complete ✓ ---")

                # ══════════════════════════════════════════════════════════
                # G13: Extrude-cut circle profile from G12 by 16 units in −Z
                # ══════════════════════════════════════════════════════════
                log(f"\n-> [G13] Extrude-cutting S5 circle (R={s5_circle['radius']:.4f}) "
                    f"by {EXTRUDE_DEPTH_G13} in +Z...")

                cx, cy = s5_circle["center"]
                z_val = s5_circle["z"]

                with BuildSketch(Plane(origin=(0, 0, z_val), z_dir=(0, 0, 1))):
                    with Locations([(cx, cy)]):
                        Circle(s5_circle["radius"])
                extrude(amount=EXTRUDE_DEPTH_G13, mode=Mode.SUBTRACT)

                vol = part_builder.part.volume
                vol_val = vol() if callable(vol) else vol
                log(f"   ✓ Volume after G13 = {vol_val:.4f} mm³")
                log("--- [G13] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # Extract final solid from BuildPart context
    # ══════════════════════════════════════════════════════════════════════
    final_solid = part_builder.part

    # ══════════════════════════════════════════════════════════════════════
    # G3 (Final): Watertight check + Export STL + Summary
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G3] Watertight check before export...")
    watertight_check(final_solid, log)

    vol = final_solid.volume
    vol_val = vol() if callable(vol) else vol
    log(f"\n   Final volume = {vol_val:.4f} mm³")

    stl_path = os.path.join(BASE_DIR, STL_NAME)
    try:
        export_stl(final_solid, stl_path, tolerance=0.005, angular_tolerance=0.05)
        stl_kb = os.path.getsize(stl_path) / 1024
        log(f"   ✓ Saved: {STL_NAME} ({stl_kb:.1f} KB)")
    except Exception as e:
        log(f"   ❌ STL export failed: {e}")

    log(f"\n{'='*60}")
    log(f"  BUILD COMPLETE — G1 through G13")
    log(f"{'='*60}")

    log_path = os.path.join(BASE_DIR, LOG_NAME)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    print(f"\n📄 Saved summary → {LOG_NAME}")

    print("Displaying in OCP viewer on port 3939...")
    set_port(3939)
    show([final_solid], names=["Art4Optodisk_G1-G13"])


if __name__ == "__main__":
    main()