"""
3_1_Art4BodyFan_build123d.py

Build the Art4BodyFan part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4BodyFan.stl

  G1:  Read S1 — 22 line segments at Z=50 forming a single enclosed profile.
       The profile is a half-box shape: straight left edge (X=0) from Y=-25 to Y=25,
       top/bottom horizontal edges, and a curved right edge (discretized arc).
       Chain line segments into a closed polygon and make a face.
  G2:  Extrude enclosed profile 50 units in −Z direction.
  G3:  Export STL + summary log (deferred to end of script).
  G4:  Read S2 — 4 line segments forming a rectangular profile on the YZ plane (X=0).
       Rectangle spans Y=[-20.5, 20.5], Z=[4.5, 45.5].
  G5:  Extrude-cut rectangular profile from G4 by 11 units in +X direction.
  G6:  Read S3 — lines + arcs + circles at X=11 forming 5 enclosed profiles:
       1 arc-slot profile (D-shaped opening with flat top/bottom),
       4 screw-hole circles (R=1.7 each).
  G7:  Extrude-cut the 5 enclosed profiles from G6 by 10 units in +X direction.
  G3:  (Final) Watertight check, volume report, export STL + summary.

Bug-avoidance notes:
  - S1 profile is a polygon of line segments (no arcs/circles) → Polyline + make_face.
  - S2 rectangle on YZ plane → sketch on Plane.YZ offset to X=0.
  - S3 arc-slot is built from chained lines + ThreePointArc in YZ plane at X=11.
  - S3 circles are fit from 3 points using circumcircle formula.
  - All extrude-cuts use OCP prism approach for non-standard plane orientations.
"""

import os
import csv
import math
from build123d import *
from ocp_vscode import show, set_port
from datetime import datetime

# ── PATHS & CONFIG ───────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/3_Art4BodyFan"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_RANGE   = "1_7"
STL_NAME  = f"3_Art4BodyFan_G_{G_RANGE}.stl"
LOG_NAME  = f"3_Art4BodyFan_summary_G_{G_RANGE}.txt"

EXTRUDE_DEPTH_G2 = 50.0   # G2: S1 profile extrude in −Z
EXTRUDE_DEPTH_G5 = 11.0   # G5: S2 rectangle cut in +X
EXTRUDE_DEPTH_G7 = 10.0   # G7: S3 profiles cut in +X

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

def circle_from_3_points_2d(p1, p2, p3):
    """Compute circumcircle center and radius from 3 points in 2D."""
    ax, ay = p1[0], p1[1]
    bx, by = p2[0], p2[1]
    cx, cy = p3[0], p3[1]
    D = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(D) < 1e-12:
        raise ValueError("Collinear points — cannot fit circle.")
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / D
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / D
    return (ux, uy), math.sqrt((ax - ux)**2 + (ay - uy)**2)


def order_line_segments(rows):
    """Chain unordered line segments into closed loops."""
    segs = [(r["p1"], r["p2"]) for r in rows if r["draw_type"] == "line" and r["p2"]]
    if not segs:
        return []

    def close(a, b, tol=1e-3):
        return math.sqrt(sum((x - y)**2 for x, y in zip(a, b))) < tol

    used = set()
    loops = []
    for start_idx in range(len(segs)):
        if start_idx in used:
            continue
        loop = [segs[start_idx][0], segs[start_idx][1]]
        used.add(start_idx)
        for _ in range(len(segs)):
            added = False
            for i, (p1, p2) in enumerate(segs):
                if i in used:
                    continue
                if close(loop[-1], p1):
                    loop.append(p2); used.add(i); added = True; break
                elif close(loop[-1], p2):
                    loop.append(p1); used.add(i); added = True; break
            if not added:
                break
        if len(loop) > 2 and close(loop[0], loop[-1]):
            loop.pop()
        loops.append(loop)
    return loops


def order_segments_with_arcs(rows):
    """
    Chain line segments and 3-point arcs into closed loops.
    Returns a list of 'instructions': each is either
      ("line", p_start, p_end) or ("arc", p_start, p_mid, p_end).
    Lines and arcs share endpoints, so we chain them by matching endpoints.
    """
    # Separate lines and arcs
    elements = []  # (type, start, end, [mid_for_arc], row)
    for r in rows:
        dt = r["draw_type"]
        if dt == "line" and r["p2"]:
            elements.append(("line", r["p1"], r["p2"], None))
        elif "3_point_arc" in dt and r["p2"] and r["p3"]:
            # Arc: p1=start, p2=mid, p3=end
            elements.append(("arc", r["p1"], r["p3"], r["p2"]))

    if not elements:
        return []

    def close(a, b, tol=1e-3):
        return math.sqrt(sum((x - y)**2 for x, y in zip(a, b))) < tol

    used = set()
    loops = []

    for start_idx in range(len(elements)):
        if start_idx in used:
            continue
        etype, start, end, mid = elements[start_idx]
        chain = [(etype, start, end, mid)]
        used.add(start_idx)
        current_end = end

        for _ in range(len(elements)):
            found = False
            for i, (et, s, e, m) in enumerate(elements):
                if i in used:
                    continue
                if close(current_end, s):
                    chain.append((et, s, e, m))
                    used.add(i)
                    current_end = e
                    found = True
                    break
                elif close(current_end, e):
                    # Reverse: swap start/end
                    chain.append((et, e, s, m))
                    used.add(i)
                    current_end = s
                    found = True
                    break
            if not found:
                break

        # Check if loop is closed
        if len(chain) > 1 and close(chain[0][1], current_end):
            loops.append(chain)

    return loops


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
    log("  3_Art4BodyFan — build123d Assembly Script")
    log(f"  Guidelines: G1 → G7  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # ══════════════════════════════════════════════════════════════════════
    # G1: Read S1 — 22 line segments forming enclosed profile at Z=50
    #     Profile: half-box with curved right edge (discretized arc)
    #     Left edge at X=0 (straight), right edge is arc-approximation
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — line segments forming enclosed profile at Z=50...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")
    if not s1_rows:
        log("   ❌ No data in S1. Aborting."); return

    # All rows are lines — chain them into a closed loop
    s1_line_rows = [r for r in s1_rows if r["draw_type"] == "line"]
    s1_loops = order_line_segments(s1_line_rows)

    if not s1_loops:
        log("   ❌ Could not form closed loop from S1. Aborting."); return

    profile_loop = s1_loops[0]
    z_plane_s1 = profile_loop[0][2]  # Should be 50.0

    log(f"   Found {len(s1_loops)} closed loop(s).")
    log(f"   Profile loop: {len(profile_loop)} points at Z={z_plane_s1}")

    xs = [p[0] for p in profile_loop]
    ys = [p[1] for p in profile_loop]
    log(f"   X range: [{min(xs):.3f}, {max(xs):.3f}]")
    log(f"   Y range: [{min(ys):.3f}, {max(ys):.3f}]")

    # Build the 2D profile sketch at Z=50
    with BuildPart() as part_builder:
        with BuildSketch(Plane(origin=(0, 0, z_plane_s1), z_dir=(0, 0, 1))):
            with BuildLine():
                pts_2d = [(p[0], p[1]) for p in profile_loop]
                Polyline(*pts_2d, pts_2d[0])
            make_face()

        log(f"   ✓ Profile sketch created with {len(profile_loop)} vertices.")
        log("--- [G1] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G2: Extrude enclosed profile 50 units in −Z
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G2] Extruding profile {EXTRUDE_DEPTH_G2} in −Z...")
        extrude(amount=-EXTRUDE_DEPTH_G2)
        vol = part_builder.part.volume
        vol_val = vol() if callable(vol) else vol
        log(f"   ✓ Volume after G2 = {vol_val:.4f} mm³")
        log("--- [G2] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G4: Read S2 — rectangular profile at X=0 (YZ plane)
        #     Rectangle: Y=[-20.5, 20.5], Z=[4.5, 45.5]
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G4] Reading S2 — rectangular profile on YZ plane (X=0)...")
        s2_rows = read_csv("Fusion_Coordinates_S2.csv")

        if not s2_rows:
            log("   ❌ No data in S2. Skipping G4-G5.")
        else:
            s2_line_rows = [r for r in s2_rows if r["draw_type"] == "line"]
            s2_loops = order_line_segments(s2_line_rows)
            if s2_loops:
                rect_loop = s2_loops[0]
                log(f"   Rectangle: {len(rect_loop)} points")
                for i, p in enumerate(rect_loop):
                    log(f"     P{i+1}: ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})")
                log("--- [G4] Complete ✓ ---")

                # ══════════════════════════════════════════════════════════
                # G5: Extrude-cut rectangle 11 units in +X
                #     The rectangle is on the YZ plane at X=0.
                #     We sketch on Plane.YZ and extrude in +X.
                # ══════════════════════════════════════════════════════════
                log(f"\n-> [G5] Extrude-cutting rectangle by {EXTRUDE_DEPTH_G5} in +X...")

                # The rectangle in YZ plane: use Y,Z as sketch coordinates
                # Plane.YZ has origin at (0,0,0), x_dir=(0,1,0), y_dir=(0,0,1), z_dir=(1,0,0)
                # So sketch X=Y_world, sketch Y=Z_world, extrude along z_dir=+X_world
                yz_pts = [(p[1], p[2]) for p in rect_loop]

                with BuildSketch(Plane.YZ):
                    with BuildLine():
                        Polyline(*yz_pts, yz_pts[0])
                    make_face()
                extrude(amount=EXTRUDE_DEPTH_G5, mode=Mode.SUBTRACT)

                vol = part_builder.part.volume
                vol_val = vol() if callable(vol) else vol
                log(f"   ✓ Volume after G5 = {vol_val:.4f} mm³")
                log("--- [G5] Complete ✓ ---")
            else:
                log("   ❌ Could not form rectangle from S2.")

        # ══════════════════════════════════════════════════════════════════
        # G6: Read S3 — profiles at X=11 (YZ plane)
        #     Contains: 14 line segments + 2 three-point arcs → 1 arc-slot
        #               4 three-point circles → 4 screw holes
        #     Total: 5 enclosed profiles
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G6] Reading S3 — arc-slot + 4 circles at X=11...")
        s3_rows = read_csv("Fusion_Coordinates_S3.csv")

        s3_circles = []
        s3_arc_rows = []
        s3_line_rows = []

        if not s3_rows:
            log("   ❌ No data in S3. Skipping G6-G7.")
        else:
            for r in s3_rows:
                if "3_point_circle" in r["draw_type"]:
                    # Compute circle center and radius in YZ plane
                    p1_yz = (r["p1"][1], r["p1"][2])
                    p2_yz = (r["p2"][1], r["p2"][2])
                    p3_yz = (r["p3"][1], r["p3"][2])
                    center, radius = circle_from_3_points_2d(p1_yz, p2_yz, p3_yz)
                    s3_circles.append({
                        "center_yz": center,
                        "radius": radius,
                        "x_val": r["p1"][0],
                        "label": r["draw_type"],
                    })
                    log(f"   ✓ {r['draw_type']}: center(Y,Z)=({center[0]:.3f}, {center[1]:.3f}), R={radius:.3f}")
                elif "3_point_arc" in r["draw_type"]:
                    s3_arc_rows.append(r)
                    log(f"   ✓ {r['draw_type']}: ({r['p1'][1]:.3f},{r['p1'][2]:.3f}) "
                        f"mid=({r['p2'][1]:.3f},{r['p2'][2]:.3f}) "
                        f"end=({r['p3'][1]:.3f},{r['p3'][2]:.3f})")
                elif r["draw_type"] == "line":
                    s3_line_rows.append(r)

            log(f"   Lines: {len(s3_line_rows)}, Arcs: {len(s3_arc_rows)}, Circles: {len(s3_circles)}")

            # Build the arc-slot chain: lines + arcs → one closed profile
            # The slot profile consists of line segments forming flat top/bottom
            # plus two arcs forming the curved left/right sides
            arc_slot_chain = order_segments_with_arcs(
                s3_line_rows + s3_arc_rows
            )

            if arc_slot_chain:
                log(f"   Arc-slot loops found: {len(arc_slot_chain)}")
                for i, chain in enumerate(arc_slot_chain):
                    log(f"     Loop {i+1}: {len(chain)} segments "
                        f"({sum(1 for e in chain if e[0]=='line')} lines, "
                        f"{sum(1 for e in chain if e[0]=='arc')} arcs)")
            else:
                log("   ⚠️  Could not chain arc-slot segments.")

            log("--- [G6] Complete ✓ ---")

            # ══════════════════════════════════════════════════════════════
            # G7: Extrude-cut S3 profiles by 10 units in +X
            #     All profiles are at X=11, cut goes in +X direction.
            #     We use OCP prism extrusion for the arc-slot (complex shape)
            #     and build123d Circle for the simple screw holes.
            # ══════════════════════════════════════════════════════════════
            log(f"\n-> [G7] Extrude-cutting S3 profiles by {EXTRUDE_DEPTH_G7} in +X...")

            x_plane = 11.0  # S3 profiles are at X=11

            # --- Cut 1: Arc-slot profile ---
            if arc_slot_chain:
                log("   Building arc-slot profile on YZ plane at X=11...")

                from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Vec, gp_Circ
                from OCP.GC import GC_MakeArcOfCircle
                from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                                 BRepBuilderAPI_MakeWire,
                                                 BRepBuilderAPI_MakeFace)
                from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

                for loop_idx, chain in enumerate(arc_slot_chain):
                    wire_maker = BRepBuilderAPI_MakeWire()

                    for seg_type, seg_start, seg_end, seg_mid in chain:
                        if seg_type == "line":
                            edge = BRepBuilderAPI_MakeEdge(
                                gp_Pnt(*seg_start),
                                gp_Pnt(*seg_end)
                            ).Edge()
                            wire_maker.Add(edge)
                        elif seg_type == "arc":
                            # 3-point arc: start, mid, end (all 3D)
                            arc = GC_MakeArcOfCircle(
                                gp_Pnt(*seg_start),
                                gp_Pnt(*seg_mid),
                                gp_Pnt(*seg_end)
                            )
                            edge = BRepBuilderAPI_MakeEdge(arc.Value()).Edge()
                            wire_maker.Add(edge)

                    if wire_maker.IsDone():
                        wire = wire_maker.Wire()
                        face = BRepBuilderAPI_MakeFace(wire)

                        if face.IsDone():
                            # Extrude in +X direction
                            prism_vec = gp_Vec(EXTRUDE_DEPTH_G7, 0, 0)
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
                                    log(f"   ✓ Arc-slot {loop_idx+1} cut. Volume = {vol_val:.4f} mm³")
                                else:
                                    log(f"   ⚠️  Arc-slot {loop_idx+1}: no solid after cut.")
                            else:
                                log(f"   ❌ Arc-slot {loop_idx+1}: prism extrusion failed.")
                        else:
                            log(f"   ❌ Arc-slot {loop_idx+1}: face creation failed.")
                    else:
                        log(f"   ❌ Arc-slot {loop_idx+1}: wire creation failed.")

            # --- Cut 2: 4 screw-hole circles ---
            if s3_circles:
                log(f"   Cutting {len(s3_circles)} screw-hole circles...")

                from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Vec, gp_Circ
                from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                                 BRepBuilderAPI_MakeWire,
                                                 BRepBuilderAPI_MakeFace)
                from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

                for i, c in enumerate(s3_circles):
                    cy, cz = c["center_yz"]
                    r = c["radius"]

                    try:
                        # Circle on YZ plane at X=x_plane, normal pointing +X
                        axis2 = gp_Ax2(
                            gp_Pnt(x_plane, cy, cz),
                            gp_Dir(1, 0, 0)  # Normal in +X
                        )
                        circ = gp_Circ(axis2, r)
                        edge = BRepBuilderAPI_MakeEdge(circ).Edge()
                        wire = BRepBuilderAPI_MakeWire(edge).Wire()
                        face = BRepBuilderAPI_MakeFace(wire).Face()

                        # Prism along +X
                        prism_vec = gp_Vec(EXTRUDE_DEPTH_G7, 0, 0)
                        prism = BRepPrimAPI_MakePrism(face, prism_vec)

                        if prism.IsDone():
                            result_shape = cut_solid_with_tool(
                                part_builder.part.wrapped, prism.Shape()
                            )
                            extracted = extract_largest_solid(result_shape)
                            if extracted:
                                part_builder._part = extracted
                                vol = extracted.volume
                                vol_val = vol() if callable(vol) else vol
                                log(f"   ✓ Circle {i+1} ({c['label']}) cut. "
                                    f"center=({cy:.3f},{cz:.3f}), R={r:.3f}. "
                                    f"Volume = {vol_val:.4f} mm³")
                            else:
                                log(f"   ⚠️  Circle {i+1}: no solid after cut.")
                        else:
                            log(f"   ❌ Circle {i+1}: prism extrusion failed.")

                    except Exception as e:
                        log(f"   ❌ Circle {i+1}: error — {e}")

            vol = part_builder.part.volume
            vol_val = vol() if callable(vol) else vol
            log(f"   Volume after G7 = {vol_val:.4f} mm³")
            log("--- [G7] Complete ✓ ---")

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
    log(f"  BUILD COMPLETE — G1 through G7")
    log(f"{'='*60}")

    log_path = os.path.join(BASE_DIR, LOG_NAME)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    print(f"\n📄 Saved summary → {LOG_NAME}")

    print("Displaying in OCP viewer on port 3939...")
    set_port(3939)
    show([final_solid], names=["Art4BodyFan_G1-G7"])


if __name__ == "__main__":
    main()