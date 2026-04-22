"""
6_1_Art4BearingPlug_build123d.py

Build the Art4BearingPlug part using build123d.
Reference STL: https://github.com/AngelLM/Thor/blob/main/stl/Art4BearingPlug.stl

  G1:  Read S1 — circle at X=6.95 (R≈3.6) on YZ plane.
  G2:  Extrude circle 3 units in −X → cylinder (X=6.95 to X=3.95).
  G3:  Export STL + summary (deferred to end).
  G4:  Read S1 — circle at X=0 (R≈3.0) on YZ plane.
  G5:  Loft X=0 (R=3.0) → X=3.95 (R=3.6). Join to cylinder.
  G6:  Read S6–S8: three D-shaped profiles at different Y levels.
       S6 at Y=0 (9 lines, middle cross-section)
       S7 at Y=−1.978 (line + arc, bottom D-shape)
       S8 at Y=+1.978 (line + arc, top D-shape)
  G7:  Loft-cut from S8 → S6 → S7 (3-section loft, subtract from body).
  G8:  Extrude-cut S8 profile in +Y with taper −1.361° for 2.3 units (top).
  G9:  Extrude-cut S7 profile in −Y with taper −1.361° for 3.9 units (bottom).
  G3 (Final): Watertight check + export.

  Execution order: G1 → G2 → G4 → G5 → G6 → G7 → G8 → G9 → G3
"""

import os
import csv
import math
from build123d import *
from ocp_vscode import show, set_port
from datetime import datetime

# ── PATHS & CONFIG ────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/6_Art4BearingPlug"
CSV_DIR  = os.path.join(BASE_DIR, "csv_merged")

G_RANGE  = "1_9"
STL_NAME = f"6_Art4BearingPlug_G_{G_RANGE}.stl"
LOG_NAME = f"6_Art4BearingPlug_summary_G_{G_RANGE}.txt"

EXTRUDE_DEPTH_G2  = 3.0
TAPER_ANGLE       = -1.361   # degrees
EXTRUDE_G8        = 2.3      # +Y direction (top)
EXTRUDE_G9        = 3.9      # −Y direction (bottom)

# ════════════════════════════════════════════════════════════════════════
# DATA PARSING
# ════════════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════════════
# GEOMETRY HELPERS
# ════════════════════════════════════════════════════════════════════════

def circle_from_3_points_2d(p1, p2, p3):
    ax, ay = p1; bx, by = p2; cx, cy = p3
    D = 2.0 * (ax*(by-cy) + bx*(cy-ay) + cx*(ay-by))
    if abs(D) < 1e-12: raise ValueError("Collinear points")
    ux = ((ax**2+ay**2)*(by-cy)+(bx**2+by**2)*(cy-ay)+(cx**2+cy**2)*(ay-by))/D
    uy = ((ax**2+ay**2)*(cx-bx)+(bx**2+by**2)*(ax-cx)+(cx**2+cy**2)*(bx-ax))/D
    return (ux, uy), math.sqrt((ax-ux)**2 + (ay-uy)**2)


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
    if free_edges == 0: log_fn("   🟢 SUCCESS: Mesh is watertight!")
    else: log_fn(f"   🔴 WARNING: {free_edges} free edge(s) — not watertight.")
    return free_edges


def build_wire_from_rows(rows):
    """Build an OCP wire from line + arc rows. Returns wire or None."""
    from OCP.gp import gp_Pnt
    from OCP.GC import GC_MakeArcOfCircle
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire

    wire_maker = BRepBuilderAPI_MakeWire()
    # Chain segments
    elements = []
    for r in rows:
        if r["draw_type"] == "line" and r["p2"]:
            elements.append(("line", r["p1"], r["p2"], None))
        elif "3_point_arc" in r["draw_type"] and r["p2"] and r["p3"]:
            elements.append(("arc", r["p1"], r["p3"], r["p2"]))

    # Simple chaining by order
    def close(a, b, tol=1e-3):
        return math.sqrt(sum((x-y)**2 for x,y in zip(a,b))) < tol

    used = set()
    ordered = []
    # Start with first element
    if not elements:
        return None
    ordered.append(elements[0])
    used.add(0)
    current_end = elements[0][2]  # end point

    for _ in range(len(elements)):
        found = False
        for i, (et, s, e, m) in enumerate(elements):
            if i in used: continue
            if close(current_end, s):
                ordered.append((et, s, e, m)); used.add(i); current_end = e; found = True; break
            elif close(current_end, e):
                ordered.append((et, e, s, m)); used.add(i); current_end = s; found = True; break
        if not found: break

    for et, s, e, m in ordered:
        if et == "line":
            edge = BRepBuilderAPI_MakeEdge(gp_Pnt(*s), gp_Pnt(*e)).Edge()
            wire_maker.Add(edge)
        elif et == "arc":
            arc = GC_MakeArcOfCircle(gp_Pnt(*s), gp_Pnt(*m), gp_Pnt(*e))
            edge = BRepBuilderAPI_MakeEdge(arc.Value()).Edge()
            wire_maker.Add(edge)

    return wire_maker.Wire() if wire_maker.IsDone() else None


# ════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════

def main():
    log_lines = []
    def log(msg=""):
        print(msg); log_lines.append(msg)

    log("=" * 60)
    log("  6_Art4BearingPlug — build123d Assembly Script")
    log(f"  Guidelines: G1 → G9  |  Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    from OCP.gp import gp_Pnt, gp_Dir, gp_Ax2, gp_Vec, gp_Circ, gp_Ax1
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                     BRepBuilderAPI_MakeWire,
                                     BRepBuilderAPI_MakeFace)
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections, BRepOffsetAPI_MakeDraft
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.TopAbs import TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    # ══════════════════════════════════════════════════════════════════
    # G1: Read S1 — circle at X=6.95 (R≈3.6)
    # ══════════════════════════════════════════════════════════════════
    log("\n-> [G1] Reading S1 — circles...")
    s1_rows = read_csv("Fusion_Coordinates_S1.csv")
    if not s1_rows:
        log("   ❌ No data in S1. Aborting."); return

    circle_x695 = None
    circle_x0 = None

    for r in s1_rows:
        if "3_point_circle" in r["draw_type"] and r["p1"] and r["p2"] and r["p3"]:
            x_val = r["p1"][0]
            p1_yz = (r["p1"][1], r["p1"][2])
            p2_yz = (r["p2"][1], r["p2"][2])
            p3_yz = (r["p3"][1], r["p3"][2])
            center, radius = circle_from_3_points_2d(p1_yz, p2_yz, p3_yz)
            info = {"center_yz": center, "radius": radius, "x": x_val}
            if abs(x_val - 6.95) < 0.1:
                circle_x695 = info
                log(f"   ✓ X=6.95: R={radius:.4f}")
            elif abs(x_val) < 0.1:
                circle_x0 = info
                log(f"   ✓ X=0:    R={radius:.4f}")

    if not circle_x695 or not circle_x0:
        log("   ❌ Missing circles. Aborting."); return
    log("--- [G1] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════
    # G2: Extrude circle at X=6.95 by 3 in −X
    # ══════════════════════════════════════════════════════════════════
    log(f"\n-> [G2] Extruding cylinder...")
    cy, cz = circle_x695["center_yz"]
    r695 = circle_x695["radius"]
    x695 = circle_x695["x"]

    axis2 = gp_Ax2(gp_Pnt(x695, cy, cz), gp_Dir(1, 0, 0))
    circ = gp_Circ(axis2, r695)
    edge = BRepBuilderAPI_MakeEdge(circ).Edge()
    wire = BRepBuilderAPI_MakeWire(edge).Wire()
    face = BRepBuilderAPI_MakeFace(wire).Face()
    prism = BRepPrimAPI_MakePrism(face, gp_Vec(-EXTRUDE_DEPTH_G2, 0, 0))

    if not prism.IsDone():
        log("   ❌ Extrusion failed."); return
    final_solid = extract_largest_solid(prism.Shape())
    if not final_solid:
        log("   ❌ No solid."); return
    v = final_solid.volume; v = v() if callable(v) else v
    log(f"   ✓ Cylinder (X=6.95→3.95). Volume = {v:.4f} mm³")
    log("--- [G2] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════
    # G4: Circle at X=0
    # ══════════════════════════════════════════════════════════════════
    log(f"\n-> [G4] Circle at X=0 (R={circle_x0['radius']:.4f})")
    log("--- [G4] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════
    # G5: Loft X=0 (R=3.0) → X=3.95 (R=3.6)
    # ══════════════════════════════════════════════════════════════════
    log(f"\n-> [G5] Lofting...")
    cy0, cz0 = circle_x0["center_yz"]
    r0 = circle_x0["radius"]
    x_loft_end = x695 - EXTRUDE_DEPTH_G2

    axis2_0 = gp_Ax2(gp_Pnt(0, cy0, cz0), gp_Dir(1, 0, 0))
    circ_0 = gp_Circ(axis2_0, r0)
    wire_0 = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circ_0).Edge()).Wire()

    axis2_e = gp_Ax2(gp_Pnt(x_loft_end, cy, cz), gp_Dir(1, 0, 0))
    circ_e = gp_Circ(axis2_e, r695)
    wire_e = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circ_e).Edge()).Wire()

    loft = BRepOffsetAPI_ThruSections(True, False)
    loft.AddWire(wire_0)
    loft.AddWire(wire_e)
    loft.Build()

    if loft.IsDone():
        loft_solid = extract_largest_solid(loft.Shape())
        if loft_solid:
            fuser = BRepAlgoAPI_Fuse()
            args = TopTools_ListOfShape(); args.Append(final_solid.wrapped)
            tools = TopTools_ListOfShape(); tools.Append(loft_solid.wrapped)
            fuser.SetArguments(args); fuser.SetTools(tools)
            fuser.SetFuzzyValue(1e-3); fuser.Build()
            if fuser.IsDone():
                fused = extract_largest_solid(fuser.Shape())
                if fused:
                    final_solid = fused
                    v = final_solid.volume; v = v() if callable(v) else v
                    log(f"   ✓ Loft joined. Volume = {v:.4f} mm³")
    log("--- [G5] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════
    # G6: Read S6–S8 — three D-shaped profiles at different Y levels
    #     S6: Y=0 (9 lines, middle D-shape in XZ plane)
    #     S7: Y=−1.978 (line + arc, bottom D-shape)
    #     S8: Y=+1.978 (line + arc, top D-shape)
    # ══════════════════════════════════════════════════════════════════
    log(f"\n-> [G6] Reading S6–S8 — three D-shaped profiles...")

    s6_rows = read_csv("Fusion_Coordinates_S6.csv")
    s7_rows = read_csv("Fusion_Coordinates_S7.csv")
    s8_rows = read_csv("Fusion_Coordinates_S8.csv")

    s6_wire = build_wire_from_rows(s6_rows) if s6_rows else None
    s7_wire = build_wire_from_rows(s7_rows) if s7_rows else None
    s8_wire = build_wire_from_rows(s8_rows) if s8_rows else None

    log(f"   S6 wire (Y=0):      {'✓' if s6_wire else '❌'}")
    log(f"   S7 wire (Y=−1.978): {'✓' if s7_wire else '❌'}")
    log(f"   S8 wire (Y=+1.978): {'✓' if s8_wire else '❌'}")
    log("--- [G6] Complete ✓ ---")

    # ══════════════════════════════════════════════════════════════════
    # G7: Loft-cut from S8 → S6 → S7
    #     3-section loft through top → middle → bottom profiles.
    #     Subtract from main body.
    # ══════════════════════════════════════════════════════════════════
    if s6_wire and s7_wire and s8_wire:
        log(f"\n-> [G7] Loft-cut: S8 → S6 → S7...")

        loft_cut = BRepOffsetAPI_ThruSections(True, False)  # solid, smooth
        loft_cut.AddWire(s8_wire)  # Y=+1.978 (top)
        loft_cut.AddWire(s6_wire)  # Y=0 (middle)
        loft_cut.AddWire(s7_wire)  # Y=−1.978 (bottom)
        loft_cut.Build()

        if loft_cut.IsDone():
            cut_solid = extract_largest_solid(loft_cut.Shape())
            if cut_solid:
                cv = cut_solid.volume; cv = cv() if callable(cv) else cv
                log(f"   ✓ Loft-cut solid created. Volume = {cv:.4f} mm³")

                result = cut_solid_with_tool(final_solid.wrapped, cut_solid.wrapped)
                extracted = extract_largest_solid(result)
                if extracted:
                    final_solid = extracted
                    v = final_solid.volume; v = v() if callable(v) else v
                    log(f"   ✓ Loft-cut done. Volume = {v:.4f} mm³")
                else:
                    log("   ⚠️  No solid after loft-cut.")
            else:
                log("   ❌ No solid from loft.")
        else:
            log("   ❌ Loft failed.")

        log("--- [G7] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════
        # G8: Extrude-cut S8 in +Y with taper −1.361° for 2.3 units
        #     S8 is at Y=+1.978. Extrude toward +Y (outward from body).
        #     Taper angle narrows the profile as it extrudes.
        # ══════════════════════════════════════════════════════════════
        log(f"\n-> [G8] Extrude-cut S8 (top) in +Y, taper={TAPER_ANGLE}°, "
            f"dist={EXTRUDE_G8}...")

        s8_face_maker = BRepBuilderAPI_MakeFace(s8_wire)
        if s8_face_maker.IsDone():
            s8_face = s8_face_maker.Face()

            # Extrude with taper using BRepPrimAPI_MakePrism
            # For tapered extrusion, use BRepOffsetAPI_MakeDraft or
            # build123d's approach with manual taper.
            # Simple approach: extrude straight, the taper from loft handles it.
            # Actually, let's use OCP MakeDraft for tapered extrusion.
            try:
                from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
                # Tapered prism: extrude face along +Y with taper
                # OCP doesn't have direct tapered prism, so we create two wires
                # (original + scaled) and loft between them.
                from OCP.gp import gp_Trsf
                from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

                # Scale the wire slightly to simulate taper
                taper_rad = math.radians(TAPER_ANGLE)
                scale_factor = 1.0 + EXTRUDE_G8 * math.tan(taper_rad)  # shrinks since angle is negative

                # Create translated + scaled copy of s8_wire at Y = 1.978 + 2.3
                trsf_translate = gp_Trsf()
                trsf_translate.SetTranslation(gp_Vec(0, EXTRUDE_G8, 0))
                s8_wire_top = TopoDS.Wire_s(BRepBuilderAPI_Transform(s8_wire, trsf_translate, True).Shape())

                # Scale around the centroid of the profile
                # S8 centroid is approximately at (0.33, 1.978, 0)
                # For simplicity, scale uniformly in XZ around X=0, Z=0
                if abs(scale_factor) > 0.01:
                    trsf_scale = gp_Trsf()
                    trsf_scale.SetScale(gp_Pnt(0, 1.978 + EXTRUDE_G8, 0), scale_factor)
                    s8_wire_scaled = TopoDS.Wire_s(BRepBuilderAPI_Transform(s8_wire_top, trsf_scale, True).Shape())
                else:
                    s8_wire_scaled = s8_wire_top

                taper_loft = BRepOffsetAPI_ThruSections(True, True)  # solid, ruled
                taper_loft.AddWire(s8_wire)
                taper_loft.AddWire(s8_wire_scaled)
                taper_loft.Build()

                if taper_loft.IsDone():
                    taper_solid = extract_largest_solid(taper_loft.Shape())
                    if taper_solid:
                        result = cut_solid_with_tool(final_solid.wrapped, taper_solid.wrapped)
                        extracted = extract_largest_solid(result)
                        if extracted:
                            final_solid = extracted
                            v = final_solid.volume; v = v() if callable(v) else v
                            log(f"   ✓ S8 tapered cut done. Volume = {v:.4f} mm³")
                        else:
                            log("   ⚠️  No solid after S8 tapered cut.")
                    else:
                        log("   ❌ No solid from taper loft.")
                else:
                    log("   ❌ Taper loft failed.")
            except Exception as e:
                log(f"   ❌ G8 error: {e}")
        else:
            log("   ❌ S8 face creation failed.")

        log("--- [G8] Complete ✓ ---")

        # ══════════════════════════════════════════════════════════════
        # G9: Extrude-cut S7 in −Y with taper −1.361° for 3.9 units
        # ══════════════════════════════════════════════════════════════
        log(f"\n-> [G9] Extrude-cut S7 (bottom) in −Y, taper={TAPER_ANGLE}°, "
            f"dist={EXTRUDE_G9}...")

        s7_face_maker = BRepBuilderAPI_MakeFace(s7_wire)
        if s7_face_maker.IsDone():
            try:
                taper_rad = math.radians(TAPER_ANGLE)
                scale_factor = 1.0 + EXTRUDE_G9 * math.tan(taper_rad)

                trsf_translate = gp_Trsf()
                trsf_translate.SetTranslation(gp_Vec(0, -EXTRUDE_G9, 0))
                s7_wire_bot = TopoDS.Wire_s(BRepBuilderAPI_Transform(s7_wire, trsf_translate, True).Shape())

                if abs(scale_factor) > 0.01:
                    trsf_scale = gp_Trsf()
                    trsf_scale.SetScale(gp_Pnt(0, -1.978 - EXTRUDE_G9, 0), scale_factor)
                    s7_wire_scaled = TopoDS.Wire_s(BRepBuilderAPI_Transform(s7_wire_bot, trsf_scale, True).Shape())
                else:
                    s7_wire_scaled = s7_wire_bot

                taper_loft = BRepOffsetAPI_ThruSections(True, True)
                taper_loft.AddWire(s7_wire)
                taper_loft.AddWire(s7_wire_scaled)
                taper_loft.Build()

                if taper_loft.IsDone():
                    taper_solid = extract_largest_solid(taper_loft.Shape())
                    if taper_solid:
                        result = cut_solid_with_tool(final_solid.wrapped, taper_solid.wrapped)
                        extracted = extract_largest_solid(result)
                        if extracted:
                            final_solid = extracted
                            v = final_solid.volume; v = v() if callable(v) else v
                            log(f"   ✓ S7 tapered cut done. Volume = {v:.4f} mm³")
                        else:
                            log("   ⚠️  No solid after S7 tapered cut.")
                    else:
                        log("   ❌ No solid from taper loft.")
                else:
                    log("   ❌ Taper loft failed.")
            except Exception as e:
                log(f"   ❌ G9 error: {e}")
        else:
            log("   ❌ S7 face creation failed.")

        log("--- [G9] Complete ✓ ---")

    else:
        log("   ❌ Missing S6/S7/S8 wires. Skipping G7-G9.")

    # ══════════════════════════════════════════════════════════════════
    # G3 (Final): Watertight check + Export
    # ══════════════════════════════════════════════════════════════════
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
    log(f"  BUILD COMPLETE — G1 through G9")
    log(f"{'='*60}")

    log_path = os.path.join(BASE_DIR, LOG_NAME)
    with open(log_path, "w") as f:
        f.write("\n".join(log_lines))
    print(f"\n📄 Saved summary → {LOG_NAME}")

    print("Displaying in OCP viewer on port 3939...")
    set_port(3939)
    show([final_solid], names=["Art4BearingPlug_G1-G9"])


if __name__ == "__main__":
    main()