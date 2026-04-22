"""
5_1_Art4TransmissionColumn_build123d.py

Build the Art4TransmissionColumn part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4TransmissionColumn.stl

  G1:  Read S1 — 11 line segments + 2 arcs on YZ plane (X=0).
       Report the profile data (lines and arcs).
       NOTE: S1 arcs are bad (arc2 collinear, arc1 direction wrong).
  G12: Read S5 — corrected arc coordinates.
       Discard S1 arcs, use S5 arcs instead. Combine S1 lines + S5 arcs
       → chain into a single closed revolution profile → make face.
       Arc 1 (fillet): (19.5,64) → mid(17.732,63.268) → (17,61.5)
       Arc 2 (groove): (35,65.8) → mid(31.8,69) → (35,72.2)
  G2:  Revolve corrected enclosed profile 360° about the global Z axis.
  G3:  Export STL + summary log (deferred to end of script).
  G4:  Read S2 — one 3-point circle at Z=76 (top face).
       Center ≈ (16.97, 16.97), R ≈ 1.7, at 45° from X axis, dist=24 from Z.
  G5:  Extrude-cut circle from G4 by 13 units in −Z.
  G6:  Circular pattern of G5 cut feature — 4 copies at 90° intervals around Z.
  G7:  Read S3 — four hexagonal profiles (6-sided line loops) at Z=76.
       Centroids at 45°, 135°, 225°, 315° (dist=24 from Z axis).
  G8:  Extrude-cut the 4 hexagons by 7 units in −Z.
  G9:  Read S4 — two 3-point circles at Z=64.
       Inner R ≈ 1.7, Outer R ≈ 2.95, both centered at (−28.5, 0) = 180°.
  G10: Extrude-cut inner circle 13 units in +Z, outer circle 3 units in +Z
       → countersink hole.
  G11: Circular pattern of G10 cuts — 4 copies at 90° intervals around Z.
  G13: Read S6 — front tooth profile at Z=0 (33 line segments, closed loop).
       Build OCP wire + face for the tooth cross-section.
  G14: Read S7 — back tooth profile at Z=17 (36 line segments, closed loop).
       Build OCP wire + face for the tooth cross-section at gear top.
  G15: Loft between G13 (S6 face) and G14 (S7 face) to create one tooth solid.
       Boolean-join tooth to main body.
  G16: Circular pattern — replicate G15 tooth 20 times around Z axis (360°/20 = 18° spacing).
  G3 (Final): Watertight check, volume report, export STL + summary.

  Execution order: G1 → G12 → G2 → G4–G11 → G13–G16 → G3
"""

import os
import csv
import math
from build123d import *
from ocp_vscode import show, set_port
from datetime import datetime

# ── PATHS & CONFIG ───────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/5_Art4TransmissionColumn"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_RANGE   = "1_16"
STL_NAME  = f"5_Art4TransmissionColumn_G_{G_RANGE}.stl"
LOG_NAME  = f"5_Art4TransmissionColumn_summary_G_{G_RANGE}.txt"

EXTRUDE_DEPTH_G5  = 13.0   # G5:  S2 circle cut in −Z
EXTRUDE_DEPTH_G8  = 7.0    # G8:  S3 hexagon cut in −Z
EXTRUDE_DEPTH_G10_INNER = 13.0  # G10: S4 inner circle cut in +Z
EXTRUDE_DEPTH_G10_OUTER = 3.0   # G10: S4 outer circle cut in +Z
CIRCULAR_PATTERN_COUNT  = 4     # G6, G11: 4 copies
TOOTH_COUNT             = 20    # G16: 20 teeth around gear

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
    Returns list of chains, each element: (type, start, end, mid_or_None).
    """
    elements = []
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
    log("  5_Art4TransmissionColumn — build123d Assembly Script")
    log(f"  Guidelines: G1 → G12  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    # ══════════════════════════════════════════════════════════════════════
    # G1: Read S1 — 11 line segments + 2 arcs on YZ plane (X=0)
    #     Report profile data. NOTE: S1 arcs are bad and will be replaced.
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — revolution profile segments on YZ plane...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")
    if not s1_rows:
        log("   ❌ No data in S1. Aborting."); return

    s1_lines = [r for r in s1_rows if r["draw_type"] == "line"]
    s1_arcs  = [r for r in s1_rows if "3_point_arc" in r["draw_type"]]

    log(f"   S1 total rows: {len(s1_rows)}")
    log(f"   S1 lines: {len(s1_lines)}")
    log(f"   S1 arcs:  {len(s1_arcs)} (⚠️  will be replaced by S5 in G12)")
    for r in s1_arcs:
        log(f"     {r['draw_type']}: ({r['p1'][1]:.3f},{r['p1'][2]:.3f}) "
            f"mid=({r['p2'][1]:.3f},{r['p2'][2]:.3f}) "
            f"end=({r['p3'][1]:.3f},{r['p3'][2]:.3f})  ← BAD")
    log("--- [G1] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G12: Read S5 — corrected arcs. Replace S1 arcs with S5 arcs.
    #      Combine S1 lines + S5 arcs → chain → closed profile → face.
    # ══════════════════════════════════════════════════════════════════════
    log("\n-> [G12] Reading S5 — corrected arcs to replace S1 arcs...")
    s5_rows = read_csv("Fusion_Coordinates_S5.csv")
    if not s5_rows:
        log("   ❌ No data in S5. Aborting."); return

    s5_arcs = [r for r in s5_rows if "3_point_arc" in r["draw_type"]]
    log(f"   S5 corrected arcs: {len(s5_arcs)}")
    for r in s5_arcs:
        log(f"     {r['draw_type']}: start=({r['p1'][1]:.3f},{r['p1'][2]:.3f}) "
            f"mid=({r['p2'][1]:.3f},{r['p2'][2]:.3f}) "
            f"end=({r['p3'][1]:.3f},{r['p3'][2]:.3f})  ← GOOD")

    # Combine S1 lines (good) + S5 arcs (corrected) — discard S1 arcs
    combined_rows = s1_lines + s5_arcs
    profile_chains = order_segments_with_arcs(combined_rows)

    if not profile_chains:
        log("   ❌ Could not form closed profile. Aborting."); return

    chain = profile_chains[0]
    log(f"   Found {len(profile_chains)} closed loop(s).")
    log(f"   Profile chain: {len(chain)} segments "
        f"({sum(1 for e in chain if e[0]=='line')} lines, "
        f"{sum(1 for e in chain if e[0]=='arc')} arcs)")

    # Build the profile wire using OCP for arc support
    from OCP.gp import gp_Pnt, gp_Vec, gp_Dir, gp_Ax1, gp_Ax2
    from OCP.GC import GC_MakeArcOfCircle
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                     BRepBuilderAPI_MakeWire,
                                     BRepBuilderAPI_MakeFace)
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol

    wire_maker = BRepBuilderAPI_MakeWire()

    for seg_type, seg_start, seg_end, seg_mid in chain:
        if seg_type == "line":
            edge = BRepBuilderAPI_MakeEdge(
                gp_Pnt(*seg_start), gp_Pnt(*seg_end)
            ).Edge()
            wire_maker.Add(edge)
        elif seg_type == "arc":
            arc = GC_MakeArcOfCircle(
                gp_Pnt(*seg_start), gp_Pnt(*seg_mid), gp_Pnt(*seg_end)
            )
            edge = BRepBuilderAPI_MakeEdge(arc.Value()).Edge()
            wire_maker.Add(edge)

    if not wire_maker.IsDone():
        log("   ❌ Wire creation failed. Aborting."); return

    wire = wire_maker.Wire()
    face_maker = BRepBuilderAPI_MakeFace(wire)
    if not face_maker.IsDone():
        log("   ❌ Face creation failed. Aborting."); return

    profile_face = face_maker.Face()
    log("   ✓ Corrected profile face created (S1 lines + S5 arcs).")
    log("--- [G12] Complete ✓ ---")
    log("   (G1 data read → G12 arcs fixed → profile ready for G2 revolve)")

    # ══════════════════════════════════════════════════════════════════════
    # G2: Revolve profile 360° about the global Z axis
    #     The Z axis passes through the origin: point=(0,0,0), dir=(0,0,1)
    #     The profile is on the YZ plane with Y>0 = radial distance.
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G2] Revolving profile 360° about Z axis...")

    z_axis = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1))
    revolver = BRepPrimAPI_MakeRevol(profile_face, z_axis, math.radians(360.0))

    if not revolver.IsDone():
        log("   ❌ Revolve failed. Aborting."); return

    revolved_shape = revolver.Shape()
    final_solid = extract_largest_solid(revolved_shape)
    if not final_solid:
        log("   ❌ No solid from revolve. Aborting."); return

    vol = final_solid.volume
    vol_val = vol() if callable(vol) else vol
    log(f"   ✓ Revolved solid created. Volume = {vol_val:.4f} mm³")
    log("--- [G2] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G4: Read S2 — one 3-point circle at Z=76 (top face)
    #     Center ≈ (16.97, 16.97), R ≈ 1.7, at 45° angle, dist=24
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G4] Reading S2 — circle at Z=76 (top face)...")
    s2_rows = read_csv("Fusion_Coordinates_S2.csv")

    s2_circle = None
    if not s2_rows:
        log("   ❌ No data in S2. Skipping G4-G6.")
    else:
        for r in s2_rows:
            if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
                center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                z_val = r["p1"][2]
                s2_circle = {"center": center, "radius": radius, "z": z_val}
                log(f"   ✓ Circle: center=({center[0]:.4f}, {center[1]:.4f}), "
                    f"R={radius:.4f}, Z={z_val}")

        if s2_circle:
            log("--- [G4] Complete ✓ ---")

            # ══════════════════════════════════════════════════════════════
            # G5: Extrude-cut S2 circle by 13 units in −Z
            # ══════════════════════════════════════════════════════════════
            log(f"\n-> [G5] Extrude-cutting S2 circle by {EXTRUDE_DEPTH_G5} in −Z...")

            from OCP.gp import gp_Circ
            from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

            cx, cy = s2_circle["center"]
            z_val = s2_circle["z"]
            r = s2_circle["radius"]

            axis2 = gp_Ax2(gp_Pnt(cx, cy, z_val), gp_Dir(0, 0, 1))
            circ = gp_Circ(axis2, r)
            edge = BRepBuilderAPI_MakeEdge(circ).Edge()
            wire = BRepBuilderAPI_MakeWire(edge).Wire()
            face = BRepBuilderAPI_MakeFace(wire).Face()

            prism_vec = gp_Vec(0, 0, -EXTRUDE_DEPTH_G5)
            prism = BRepPrimAPI_MakePrism(face, prism_vec)

            if prism.IsDone():
                result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                extracted = extract_largest_solid(result_shape)
                if extracted:
                    final_solid = extracted
                    vol_val = final_solid.volume
                    vol_val = vol_val() if callable(vol_val) else vol_val
                    log(f"   ✓ S2 circle cut. Volume = {vol_val:.4f} mm³")

            log("--- [G5] Complete ✓ ---")

            # ══════════════════════════════════════════════════════════════
            # G6: Circular pattern of G5 — 4 copies at 90° around Z axis
            # ══════════════════════════════════════════════════════════════
            log(f"\n-> [G6] Circular pattern — {CIRCULAR_PATTERN_COUNT} holes at 90°...")

            hole_dist = math.sqrt(cx**2 + cy**2)
            base_angle = math.atan2(cy, cx)
            log(f"   Original hole at ({cx:.3f}, {cy:.3f}), dist={hole_dist:.3f}, "
                f"angle={math.degrees(base_angle):.1f}°")

            for copy_idx in range(1, CIRCULAR_PATTERN_COUNT):
                angle = base_angle + copy_idx * (2 * math.pi / CIRCULAR_PATTERN_COUNT)
                cx_rot = hole_dist * math.cos(angle)
                cy_rot = hole_dist * math.sin(angle)

                log(f"   Copy {copy_idx+1}: angle={math.degrees(angle):.1f}°, "
                    f"center=({cx_rot:.3f}, {cy_rot:.3f})")

                axis2 = gp_Ax2(gp_Pnt(cx_rot, cy_rot, z_val), gp_Dir(0, 0, 1))
                circ = gp_Circ(axis2, r)
                edge = BRepBuilderAPI_MakeEdge(circ).Edge()
                wire = BRepBuilderAPI_MakeWire(edge).Wire()
                face = BRepBuilderAPI_MakeFace(wire).Face()

                prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, -EXTRUDE_DEPTH_G5))
                if prism.IsDone():
                    result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                    extracted = extract_largest_solid(result_shape)
                    if extracted:
                        final_solid = extracted

            vol_val = final_solid.volume
            vol_val = vol_val() if callable(vol_val) else vol_val
            log(f"   Volume after G6 = {vol_val:.4f} mm³")
            log("--- [G6] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G7: Read S3 — four hexagonal profiles at Z=76
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G7] Reading S3 — four hexagonal profiles at Z=76...")
    s3_rows = read_csv("Fusion_Coordinates_S3.csv")

    hex_loops = []
    if not s3_rows:
        log("   ❌ No data in S3. Skipping G7-G8.")
    else:
        s3_line_rows = [r for r in s3_rows if r["draw_type"] == "line"]
        hex_loops = order_line_segments(s3_line_rows)
        log(f"   Found {len(hex_loops)} closed polygon(s).")
        for i, loop in enumerate(hex_loops):
            cx_h = sum(p[0] for p in loop) / len(loop)
            cy_h = sum(p[1] for p in loop) / len(loop)
            log(f"   Hexagon {i+1}: {len(loop)} pts, "
                f"centroid=({cx_h:.3f}, {cy_h:.3f}), Z={loop[0][2]}")
        log("--- [G7] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G8: Extrude-cut hexagons by 7 in −Z
        # ══════════════════════════════════════════════════════════════════
        if hex_loops:
            log(f"\n-> [G8] Cutting {len(hex_loops)} hexagons by {EXTRUDE_DEPTH_G8} in −Z...")

            from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

            for i, loop in enumerate(hex_loops):
                z_hex = loop[0][2]

                hex_wire_maker = BRepBuilderAPI_MakeWire()
                for j in range(len(loop)):
                    p_start = loop[j]
                    p_end = loop[(j + 1) % len(loop)]
                    edge = BRepBuilderAPI_MakeEdge(
                        gp_Pnt(*p_start), gp_Pnt(*p_end)
                    ).Edge()
                    hex_wire_maker.Add(edge)

                if hex_wire_maker.IsDone():
                    hex_face = BRepBuilderAPI_MakeFace(hex_wire_maker.Wire())
                    if hex_face.IsDone():
                        prism = BRepPrimAPI_MakePrism(
                            hex_face.Face(), gp_Vec(0, 0, -EXTRUDE_DEPTH_G8)
                        )
                        if prism.IsDone():
                            result_shape = cut_solid_with_tool(
                                final_solid.wrapped, prism.Shape()
                            )
                            extracted = extract_largest_solid(result_shape)
                            if extracted:
                                final_solid = extracted
                                v = final_solid.volume
                                v = v() if callable(v) else v
                                log(f"   ✓ Hexagon {i+1} cut. Volume = {v:.4f} mm³")
                            else:
                                log(f"   ⚠️  Hexagon {i+1}: no solid after cut.")
                        else:
                            log(f"   ❌ Hexagon {i+1}: prism failed.")
                    else:
                        log(f"   ❌ Hexagon {i+1}: face failed.")
                else:
                    log(f"   ❌ Hexagon {i+1}: wire failed.")

            vol_val = final_solid.volume
            vol_val = vol_val() if callable(vol_val) else vol_val
            log(f"   Volume after G8 = {vol_val:.4f} mm³")
            log("--- [G8] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G9: Read S4 — two 3-point circles at Z=64 (countersink hole)
    #     Inner R ≈ 1.7 (through-hole), Outer R ≈ 2.95 (countersink)
    #     Both centered at ≈ (−28.5, 0) = 180° at dist=28.5
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G9] Reading S4 — countersink circles at Z=64...")
    s4_rows = read_csv("Fusion_Coordinates_S4.csv")

    s4_inner = None
    s4_outer = None

    if not s4_rows:
        log("   ❌ No data in S4. Skipping G9-G11.")
    else:
        s4_circles = []
        for r in s4_rows:
            if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
                center, radius = circle_from_3_points(r["p1"], r["p2"], r["p3"])
                z_val = r["p1"][2]
                s4_circles.append({"center": center, "radius": radius, "z": z_val,
                                    "label": r["draw_type"]})
                log(f"   ✓ {r['draw_type']}: center=({center[0]:.4f}, {center[1]:.4f}), "
                    f"R={radius:.4f}, Z={z_val}")

        s4_circles.sort(key=lambda c: c["radius"])
        if len(s4_circles) >= 2:
            s4_inner = s4_circles[0]  # R ≈ 1.7
            s4_outer = s4_circles[1]  # R ≈ 2.95
        log("--- [G9] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G10: Extrude-cut countersink hole
        #      Inner (R≈1.7) → 13 units in +Z
        #      Outer (R≈2.95) → 3 units in +Z
        # ══════════════════════════════════════════════════════════════════
        if s4_inner and s4_outer:
            log(f"\n-> [G10] Cutting countersink hole at Z=64...")

            from OCP.gp import gp_Circ
            from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism

            # Inner circle cut (deeper, smaller)
            cx_i, cy_i = s4_inner["center"]
            z_i = s4_inner["z"]
            r_i = s4_inner["radius"]

            axis2 = gp_Ax2(gp_Pnt(cx_i, cy_i, z_i), gp_Dir(0, 0, 1))
            circ = gp_Circ(axis2, r_i)
            edge = BRepBuilderAPI_MakeEdge(circ).Edge()
            wire = BRepBuilderAPI_MakeWire(edge).Wire()
            face = BRepBuilderAPI_MakeFace(wire).Face()
            prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, EXTRUDE_DEPTH_G10_INNER))
            if prism.IsDone():
                result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                extracted = extract_largest_solid(result_shape)
                if extracted:
                    final_solid = extracted
                    v = final_solid.volume; v = v() if callable(v) else v
                    log(f"   ✓ Inner circle (R={r_i:.3f}) cut {EXTRUDE_DEPTH_G10_INNER} in +Z. Volume = {v:.4f} mm³")

            # Outer circle cut (shallower, wider)
            cx_o, cy_o = s4_outer["center"]
            r_o = s4_outer["radius"]

            axis2 = gp_Ax2(gp_Pnt(cx_o, cy_o, z_i), gp_Dir(0, 0, 1))
            circ = gp_Circ(axis2, r_o)
            edge = BRepBuilderAPI_MakeEdge(circ).Edge()
            wire = BRepBuilderAPI_MakeWire(edge).Wire()
            face = BRepBuilderAPI_MakeFace(wire).Face()
            prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, EXTRUDE_DEPTH_G10_OUTER))
            if prism.IsDone():
                result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                extracted = extract_largest_solid(result_shape)
                if extracted:
                    final_solid = extracted
                    v = final_solid.volume; v = v() if callable(v) else v
                    log(f"   ✓ Outer circle (R={r_o:.3f}) cut {EXTRUDE_DEPTH_G10_OUTER} in +Z. Volume = {v:.4f} mm³")

            log("--- [G10] Complete ✓ ---")

            # ══════════════════════════════════════════════════════════════
            # G11: Circular pattern of G10 — 4 copies at 90° around Z
            # ══════════════════════════════════════════════════════════════
            log(f"\n-> [G11] Circular pattern — {CIRCULAR_PATTERN_COUNT} countersink holes...")

            hole_dist_cs = math.sqrt(cx_i**2 + cy_i**2)
            base_angle_cs = math.atan2(cy_i, cx_i)
            log(f"   Original hole at ({cx_i:.3f}, {cy_i:.3f}), "
                f"dist={hole_dist_cs:.3f}, angle={math.degrees(base_angle_cs):.1f}°")

            for copy_idx in range(1, CIRCULAR_PATTERN_COUNT):
                angle = base_angle_cs + copy_idx * (2 * math.pi / CIRCULAR_PATTERN_COUNT)
                cx_rot = hole_dist_cs * math.cos(angle)
                cy_rot = hole_dist_cs * math.sin(angle)

                log(f"   Copy {copy_idx+1}: angle={math.degrees(angle):.1f}°, "
                    f"center=({cx_rot:.3f}, {cy_rot:.3f})")

                # Inner circle
                axis2 = gp_Ax2(gp_Pnt(cx_rot, cy_rot, z_i), gp_Dir(0, 0, 1))
                circ = gp_Circ(axis2, r_i)
                edge = BRepBuilderAPI_MakeEdge(circ).Edge()
                wire = BRepBuilderAPI_MakeWire(edge).Wire()
                face = BRepBuilderAPI_MakeFace(wire).Face()
                prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, EXTRUDE_DEPTH_G10_INNER))
                if prism.IsDone():
                    result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                    extracted = extract_largest_solid(result_shape)
                    if extracted:
                        final_solid = extracted

                # Outer circle
                axis2 = gp_Ax2(gp_Pnt(cx_rot, cy_rot, z_i), gp_Dir(0, 0, 1))
                circ = gp_Circ(axis2, r_o)
                edge = BRepBuilderAPI_MakeEdge(circ).Edge()
                wire = BRepBuilderAPI_MakeWire(edge).Wire()
                face = BRepBuilderAPI_MakeFace(wire).Face()
                prism = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, EXTRUDE_DEPTH_G10_OUTER))
                if prism.IsDone():
                    result_shape = cut_solid_with_tool(final_solid.wrapped, prism.Shape())
                    extracted = extract_largest_solid(result_shape)
                    if extracted:
                        final_solid = extracted

                v = final_solid.volume; v = v() if callable(v) else v
                log(f"   ✓ Copy {copy_idx+1} cut. Volume = {v:.4f} mm³")

            vol_val = final_solid.volume
            vol_val = vol_val() if callable(vol_val) else vol_val
            log(f"   Volume after G11 = {vol_val:.4f} mm³")
            log("--- [G11] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G13: Read S6 — front tooth profile at Z=0
    #      33 line segments forming a closed tooth cross-section.
    #      Y range: 15.68 → 19.79 (sits on column at R≈15.75 to R≈20)
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G13] Reading S6 — front tooth profile at Z=0...")
    s6_rows = read_csv("Fusion_Coordinates_S6.csv")

    s6_face = None
    if not s6_rows:
        log("   ❌ No data in S6. Skipping G13-G16.")
    else:
        s6_line_rows = [r for r in s6_rows if r["draw_type"] == "line"]
        s6_loops = order_line_segments(s6_line_rows)

        if s6_loops:
            s6_loop = s6_loops[0]
            log(f"   ✓ S6 closed loop: {len(s6_loop)} points at Z={s6_loop[0][2]}")

            cx_s6 = sum(p[0] for p in s6_loop) / len(s6_loop)
            cy_s6 = sum(p[1] for p in s6_loop) / len(s6_loop)
            log(f"   Centroid: ({cx_s6:.3f}, {cy_s6:.3f})")

            # Build OCP wire + face
            s6_wire_maker = BRepBuilderAPI_MakeWire()
            for j in range(len(s6_loop)):
                p_start = s6_loop[j]
                p_end = s6_loop[(j + 1) % len(s6_loop)]
                edge = BRepBuilderAPI_MakeEdge(
                    gp_Pnt(*p_start), gp_Pnt(*p_end)
                ).Edge()
                s6_wire_maker.Add(edge)

            if s6_wire_maker.IsDone():
                s6_face_maker = BRepBuilderAPI_MakeFace(s6_wire_maker.Wire())
                if s6_face_maker.IsDone():
                    s6_face = s6_face_maker.Face()
                    log("   ✓ S6 face created.")
                else:
                    log("   ❌ S6 face creation failed.")
            else:
                log("   ❌ S6 wire creation failed.")
        else:
            log("   ❌ Could not form closed loop from S6.")

        log("--- [G13] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G14: Read S7 — back tooth profile at Z=17
    #      36 line segments forming a closed tooth cross-section.
    #      Centroid at ≈ (−9.16, 15.30), rotated ~121° from S6.
    # ══════════════════════════════════════════════════════════════════════
    log(f"\n-> [G14] Reading S7 — back tooth profile at Z=17...")
    s7_rows = read_csv("Fusion_Coordinates_S7.csv")

    s7_face = None
    if not s7_rows:
        log("   ❌ No data in S7. Skipping G14-G16.")
    else:
        s7_line_rows = [r for r in s7_rows if r["draw_type"] == "line"]
        s7_loops = order_line_segments(s7_line_rows)

        if s7_loops:
            s7_loop = s7_loops[0]
            log(f"   ✓ S7 closed loop: {len(s7_loop)} points at Z={s7_loop[0][2]}")

            cx_s7 = sum(p[0] for p in s7_loop) / len(s7_loop)
            cy_s7 = sum(p[1] for p in s7_loop) / len(s7_loop)
            log(f"   Centroid: ({cx_s7:.3f}, {cy_s7:.3f})")

            # Build OCP wire + face
            s7_wire_maker = BRepBuilderAPI_MakeWire()
            for j in range(len(s7_loop)):
                p_start = s7_loop[j]
                p_end = s7_loop[(j + 1) % len(s7_loop)]
                edge = BRepBuilderAPI_MakeEdge(
                    gp_Pnt(*p_start), gp_Pnt(*p_end)
                ).Edge()
                s7_wire_maker.Add(edge)

            if s7_wire_maker.IsDone():
                s7_face_maker = BRepBuilderAPI_MakeFace(s7_wire_maker.Wire())
                if s7_face_maker.IsDone():
                    s7_face = s7_face_maker.Face()
                    log("   ✓ S7 face created.")
                else:
                    log("   ❌ S7 face creation failed.")
            else:
                log("   ❌ S7 wire creation failed.")
        else:
            log("   ❌ Could not form closed loop from S7.")

        log("--- [G14] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════════
    # G15: Loft between S6 face (Z=0) and S7 face (Z=17) → one tooth
    #      Uses OCP BRepOffsetAPI_ThruSections for ruled loft.
    #      Then boolean-join the tooth to the main body.
    # ══════════════════════════════════════════════════════════════════════
    if s6_face is not None and s7_face is not None:
        log(f"\n-> [G15] Lofting S6 → S7 to create one gear tooth...")

        from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
        from OCP.TopAbs import TopAbs_WIRE
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopoDS import TopoDS

        # Extract wires from faces
        def get_outer_wire(face):
            explorer = TopExp_Explorer(face, TopAbs_WIRE)
            if explorer.More():
                return TopoDS.Wire_s(explorer.Current())
            return None

        s6_wire = get_outer_wire(s6_face)
        s7_wire = get_outer_wire(s7_face)

        if s6_wire and s7_wire:
            # ThruSections: isSolid=True, ruled=True (straight connections)
            loft_maker = BRepOffsetAPI_ThruSections(True, True)
            loft_maker.AddWire(s6_wire)
            loft_maker.AddWire(s7_wire)
            loft_maker.Build()

            if loft_maker.IsDone():
                tooth_shape = loft_maker.Shape()
                tooth_solid = extract_largest_solid(tooth_shape)

                if tooth_solid:
                    tv = tooth_solid.volume
                    tv = tv() if callable(tv) else tv
                    log(f"   ✓ Tooth loft created. Tooth volume = {tv:.4f} mm³")

                    # Boolean-join tooth to main body
                    from OCP.TopTools import TopTools_ListOfShape
                    fuser = BRepAlgoAPI_Fuse()
                    args = TopTools_ListOfShape(); args.Append(final_solid.wrapped)
                    tools = TopTools_ListOfShape(); tools.Append(tooth_solid.wrapped)
                    fuser.SetArguments(args); fuser.SetTools(tools)
                    fuser.SetFuzzyValue(1e-3); fuser.Build()

                    if fuser.IsDone():
                        fused = extract_largest_solid(fuser.Shape())
                        if fused:
                            final_solid = fused
                            v = final_solid.volume; v = v() if callable(v) else v
                            log(f"   ✓ Tooth joined to body. Volume = {v:.4f} mm³")
                        else:
                            log("   ⚠️  No solid after fuse.")
                    else:
                        log("   ❌ Boolean fuse failed.")
                else:
                    log("   ❌ No solid from loft.")
            else:
                log("   ❌ Loft (ThruSections) failed.")
        else:
            log("   ❌ Could not extract wires from faces.")

        log("--- [G15] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════════
        # G16: Circular pattern — 20 teeth around Z axis
        #      First tooth is already joined. Rotate S6/S7 profiles by
        #      18° increments (360°/20) and loft+join each copy.
        # ══════════════════════════════════════════════════════════════════
        log(f"\n-> [G16] Circular pattern — {TOOTH_COUNT} teeth at "
            f"{360.0/TOOTH_COUNT:.1f}° intervals...")

        from OCP.gp import gp_Trsf
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

        angle_step = 2 * math.pi / TOOTH_COUNT

        for tooth_idx in range(1, TOOTH_COUNT):
            angle = tooth_idx * angle_step
            log(f"   Tooth {tooth_idx+1}: angle={math.degrees(angle):.1f}°")

            # Create rotation transform around Z axis
            trsf = gp_Trsf()
            trsf.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), angle)

            # Rotate S6 wire
            s6_wire_rot = BRepBuilderAPI_Transform(s6_wire, trsf, True).Shape()
            s7_wire_rot = BRepBuilderAPI_Transform(s7_wire, trsf, True).Shape()

            # Loft the rotated wires
            loft_rot = BRepOffsetAPI_ThruSections(True, True)
            loft_rot.AddWire(TopoDS.Wire_s(s6_wire_rot))
            loft_rot.AddWire(TopoDS.Wire_s(s7_wire_rot))
            loft_rot.Build()

            if loft_rot.IsDone():
                tooth_rot = extract_largest_solid(loft_rot.Shape())
                if tooth_rot:
                    # Boolean-join to main body
                    fuser = BRepAlgoAPI_Fuse()
                    args = TopTools_ListOfShape(); args.Append(final_solid.wrapped)
                    tools = TopTools_ListOfShape(); tools.Append(tooth_rot.wrapped)
                    fuser.SetArguments(args); fuser.SetTools(tools)
                    fuser.SetFuzzyValue(1e-3); fuser.Build()

                    if fuser.IsDone():
                        fused = extract_largest_solid(fuser.Shape())
                        if fused:
                            final_solid = fused
                        else:
                            log(f"   ⚠️  Tooth {tooth_idx+1}: no solid after fuse.")
                    else:
                        log(f"   ❌ Tooth {tooth_idx+1}: fuse failed.")
                else:
                    log(f"   ⚠️  Tooth {tooth_idx+1}: no solid from loft.")
            else:
                log(f"   ❌ Tooth {tooth_idx+1}: loft failed.")

        vol_val = final_solid.volume
        vol_val = vol_val() if callable(vol_val) else vol_val
        log(f"   Volume after G16 = {vol_val:.4f} mm³ ({TOOTH_COUNT} teeth)")
        log("--- [G16] Complete ✓ ---")

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
    log(f"  BUILD COMPLETE — G1 through G16")
    log(f"{'='*60}")

    log_path = os.path.join(BASE_DIR, LOG_NAME)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    print(f"\n📄 Saved summary → {LOG_NAME}")

    print("Displaying in OCP viewer on port 3939...")
    set_port(3939)
    show([final_solid], names=["Art4TransmissionColumn_G1-G16"])


if __name__ == "__main__":
    main()