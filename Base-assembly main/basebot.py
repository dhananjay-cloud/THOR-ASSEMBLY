#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
basebot.py — Base Bot Part
============================
Build123d script to model the base bot and export STL + STEP.
"""

from build123d import *
from math import sqrt, cos, sin, radians

# ==============================================================================
#  PARAMETERS
# ==============================================================================

outer_diameter = 2000.0000011     # mm
inner_diameter = 1499.99999986    # mm
height         = 300.00000034     # mm  (z=0 to z=300.00000034)

# Pre-computed values used inside BuildPart
rect_radius = sqrt(215.0**2 + 666.16438459**2)  # = 700mm

# Pattern centres for 5× counterbore holes (original + 4 CW rotations)
_pat_r = 860.0
_pat_centres = [
    (_pat_r * cos(radians(90 - a)), _pat_r * sin(radians(90 - a)))
    for a in [60, 120, 180, 240]
]

# ==============================================================================
#  PRE-BUILD WALL MOUNT COMPONENTS (avoids deepcopy inside main part)
# ==============================================================================

# Wall mount additive solid (polygon extrusion)
with BuildPart() as _wm_add_part:
    with BuildSketch(Plane.XZ.offset(-50)):
        with BuildLine():
            Polyline(
                (-723.21199393, 655.000000),
                (-723.21199393, 481.78801383),
                (-698.21199393, 481.78801383),
                (-625.000000,   555.00001511),
                (-625.000000,   655.000000),
                close=True,
            )
        make_face()
    extrude(amount=100)
_wm_solid = _wm_add_part.part

# Pentagon cut volume
with BuildPart() as _wm_pent_part:
    with BuildSketch(Plane.XY.offset(591.50001526)):
        with BuildLine():
            Polyline(
                (-625.000000,   -29.01185036),
                (-691.75003052, -29.01185036),
                (-708.49998474,   0.000000),
                (-691.75003052,  29.01185036),
                (-625.000000,    29.01185036),
                close=True,
            )
        make_face()
    extrude(amount=618.49998474 - 591.50001526)
_wm_pent_solid = _wm_pent_part.part

# Circle cut volume (cylinder from z=475 to z=655)
with BuildPart() as _wm_circ_part:
    with BuildSketch(Plane.XY.offset(475)):
        with Locations(Location((-675.000000, 0.000000))):
            Circle(radius=33.99999354 / 2)
    extrude(amount=655 - 475)
_wm_circ_solid = _wm_circ_part.part

# ==============================================================================
#  GEOMETRY
# ==============================================================================

with BuildPart() as part:
    with BuildSketch(Plane.XY) as profile:
        Circle(radius=outer_diameter / 2)
        Circle(radius=inner_diameter / 2, mode=Mode.SUBTRACT)
    extrude(amount=height)

    # Revolve cut: circle ⌀499.99999744mm centred at (999.99999825, 299.99999966) on XZ plane
    with BuildSketch(Plane.XZ) as rev_profile:
        with Locations(Location((999.99999825, 299.99999966))):
            Circle(radius=499.99999744 / 2)
    revolve(axis=Axis.Z, revolution_arc=360, mode=Mode.SUBTRACT)

    # Triangular cut throughout the full body height
    with BuildSketch(Plane.XY) as tri_profile:
        with BuildLine() as tri_outline:
            Polyline(
                ( 470.55984026,      0.0),
                (-1063.4840476,   1534.04957186),
                (-1063.4840476,  -1534.04957186),
                close=True,
            )
        make_face()
    extrude(amount=height, mode=Mode.SUBTRACT)

    # Inner ring: outer ⌀1499.99999986mm, inner ⌀1399.99999007mm, z=0 to z=655mm
    with BuildSketch(Plane.XY) as inner_ring_profile:
        Circle(radius=1499.99999986 / 2)
        Circle(radius=1405 / 2, mode=Mode.SUBTRACT)
    extrude(amount=655)

    # Rectangle revolved 41.16314841° around Z
    rect_plane = Plane(
        origin=Vector(0, 0, 0),
        x_dir=Vector(215, -666.16438459, 0),
        z_dir=Vector(-666.16438459, -215, 0),
    )
    with BuildSketch(rect_plane) as revolve_rect:
        with BuildLine():
            Polyline(
                (0,           0.0),
                (rect_radius, 0.0),
                (rect_radius, 470.0),
                (0,           470.0),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z, revolution_arc=41.16314841)

    # Tapered circle extrusion: ⌀80.00000668mm at (-600, 300, 557.5)
    with BuildSketch(Plane.YZ.offset(-600)) as taper_profile:
        with Locations(Location((299.99999996, 557.49999992))):
            Circle(radius=80.00000668 / 2)
    extrude(amount=-89.12289868, taper=-73.73979298/2)

    # Rectangle cut on plane x=215, extruded to x=635
    with BuildSketch(Plane.YZ.offset(215)) as rect_cut_profile:
        with BuildLine():
            Polyline(
                (-294.57595624, 470.000000),
                (-360.000000,   470.000000),
                (-360.000000,    49.99932576),
                (-294.57595624,  49.99932576),
                close=True,
            )
        make_face()
    extrude(amount=420, mode=Mode.SUBTRACT)

    # Three more tapered circle extrusions
    with BuildSketch(Plane.YZ.offset(-600)) as taper_a:
        with Locations(Location((-299.99999992, 557.49999994))):
            Circle(radius=80.00000668 / 2)
    extrude(amount=-89.12289868, taper=-73.73979298/2)

    with BuildSketch(Plane.YZ.offset(-600)) as taper_b:
        with Locations(Location((-300.00000001, 197.49999999))):
            Circle(radius=80.00000668 / 2)
    extrude(amount=-89.12289868, taper=-73.73979298/2)

    with BuildSketch(Plane.YZ.offset(-600)) as taper_c:
        with Locations(Location((299.99999985, 197.50000007))):
            Circle(radius=80.00000668 / 2)
    extrude(amount=-89.12289868, taper=-73.73979298/2)

    # 4 holes ⌀44mm, 130mm deep in -X from x=-600
    with BuildSketch(Plane.YZ.offset(-600)) as holes_profile:
        for (y, z) in [
            (-299.99999992, 557.49999994),
            (-300.00000001, 197.49999999),
            ( 299.99999985, 197.50000007),
            ( 299.9999999,  557.49999882),
        ]:
            with Locations(Location((y, z))):
                Circle(radius=44 / 2)
    extrude(amount=-130, mode=Mode.SUBTRACT)

    # 4 centre-to-centre slot cuts at y=-1200
    slot_separation = 410.00000172 - 109.99999862
    slot_center_z   = (410.00000172 + 109.99999862) / 2
    slot_width      = 19.96502675
    slot_spacing    = 69.99999915
    slot_x_start    = 320.00000085

    with BuildSketch(Plane.XZ.offset(1200)) as slot_sketch:
        for i in range(4):
            x_pos = slot_x_start + i * slot_spacing
            with Locations(Location((x_pos, slot_center_z))):
                SlotCenterToCenter(slot_separation, slot_width, rotation=90)
    extrude(amount=-2400, mode=Mode.SUBTRACT)

    # Two rectangles at z=470, subtracted throughout body
    with BuildSketch(Plane.XY.offset(470)) as cut_profile:
        with BuildLine():
            Polyline(
                ( 215.000000,    55.00002146),
                ( 215.000000,  -666.16438459),
                (-215.00001338, -666.16438459),
                (-215.00001338,  55.00002146),
                close=True,
            )
        make_face()
        with BuildLine():
            Polyline(
                (600.33324308,  55.00002146),
                (600.33324308, -359.99997854),
                (215.000000,   -359.99997854),
                (215.000000,    55.00002146),
                close=True,
            )
        make_face()
    extrude(amount=-470, mode=Mode.SUBTRACT)

    # Rectangle block y=300→727
    with BuildSketch(Plane.XZ.offset(-300)) as rect_profile:
        with BuildLine() as rect_outline:
            Polyline(
                (-71.99999809, 50.00132531),
                ( 27.99999952, 50.00132531),
                ( 27.99999952, 450.000000),
                (-71.99999809, 450.000000),
                close=True,
            )
        make_face()
    extrude(amount=-427)

    # ── WALL MOUNT (3× at 0°, 120°, 240°) ──────────────────────────────────────
    for _wm_angle in [0, 120, 240]:
        add(_wm_solid.rotate(Axis.Z, _wm_angle))
        add(_wm_pent_solid.rotate(Axis.Z, _wm_angle), mode=Mode.SUBTRACT)
        add(_wm_circ_solid.rotate(Axis.Z, _wm_angle), mode=Mode.SUBTRACT)
    # ── END WALL MOUNT ───────────────────────────────────────────────────────────

    # Centre-to-centre slot at x=-1050
    with BuildSketch(Plane.YZ.offset(-1050)) as slot_yz:
        with Locations(Location((0, 150.00000393))):
            SlotCenterToCenter(150, 200.00000787, rotation=0)
    extrude(amount=650, mode=Mode.SUBTRACT)

    # Pentagon cut at z=359.50000763
    with BuildSketch(Plane.XY.offset(359.50000763)) as pent2_profile:
        with BuildLine():
            Polyline(
                ( 27.99999952, 340.98815918),
                (-38.750000,   340.98815918),
                (-55.50000191, 370.000000),
                (-38.750000,   399.01184082),
                ( 27.99999952, 399.01184082),
                close=True,
            )
        make_face()
    extrude(amount=386.50001526 - 359.50000763, mode=Mode.SUBTRACT)

    # Circle cut ⌀33.99999735mm at (-22, 370, 450), cut to z=240
    with BuildSketch(Plane.XY.offset(450)) as circ2_profile:
        with Locations(Location((-22.000000, 370.000000))):
            Circle(radius=33.99999735 / 2)
    extrude(amount=-(450 - 240), mode=Mode.SUBTRACT)

    # Repeat pentagon + circle cuts 280mm towards back face (+280mm in Y)
    with BuildSketch(Plane.XY.offset(359.50000763)) as pent3_profile:
        with BuildLine():
            Polyline(
                ( 27.99999952, 340.98815918 + 280),
                (-38.750000,   340.98815918 + 280),
                (-55.50000191, 370.000000   + 280),
                (-38.750000,   399.01184082 + 280),
                ( 27.99999952, 399.01184082 + 280),
                close=True,
            )
        make_face()
    extrude(amount=386.50001526 - 359.50000763, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY.offset(450)) as circ3_profile:
        with Locations(Location((-22.000000, 370.000000 + 280))):
            Circle(radius=33.99999735 / 2)
    extrude(amount=-(450 - 240), mode=Mode.SUBTRACT)

    # Counterbore hole at (265.00000022, -1050, 419.9999997): cb=390mm, thru=690mm
    with BuildSketch(Plane.XZ.offset(1050)) as cbore_wide:
        with Locations(Location((265.00000022, 419.9999997))):
            Circle(radius=58.999998579 / 2)
    extrude(amount=-390, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XZ.offset(1050)) as cbore_narrow:
        with Locations(Location((265.00000022, 419.9999997))):
            Circle(radius=34.000000194 / 2)
    extrude(amount=-690, mode=Mode.SUBTRACT)

    # Second counterbore (265, -1050, 100): same spec
    with BuildSketch(Plane.XZ.offset(1050)) as cbore2_wide:
        with Locations(Location((265.00000022, 99.9999997))):
            Circle(radius=58.999998579 / 2)
    extrude(amount=-390, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XZ.offset(1050)) as cbore2_narrow:
        with Locations(Location((265.00000022, 99.9999997))):
            Circle(radius=34.000000194 / 2)
    extrude(amount=-690, mode=Mode.SUBTRACT)

    # Counterbore hole at (585, -1050, 420): cb=650mm, thru=690mm
    with BuildSketch(Plane.XZ.offset(1050)) as cbore3_wide:
        with Locations(Location((585.000000, 420.000000))):
            Circle(radius=58.999998579 / 2)
    extrude(amount=-650, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XZ.offset(1050)) as cbore3_narrow:
        with Locations(Location((585.000000, 420.000000))):
            Circle(radius=34.000000194 / 2)
    extrude(amount=-690, mode=Mode.SUBTRACT)

    # Fourth counterbore (585, -1050, 100): same spec, extended for full breakthru
    with BuildSketch(Plane.XZ.offset(1050)) as cbore4_wide:
        with Locations(Location((585.000000, 100.00000085))):
            Circle(radius=58.999998579 / 2)
    extrude(amount=-650, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XZ.offset(1050)) as cbore4_narrow:
        with Locations(Location((585.000000, 100.00000085))):
            Circle(radius=34.000000194 / 2)
    extrude(amount=-695, mode=Mode.SUBTRACT)

    # Counterbore hole at (0, 860, 400): axis parallel to Z, drilling in -Z
    with BuildSketch(Plane.XY.offset(400)) as cbore5_wide:
        with Locations(Location((0.000000, 860.000000))):
            Circle(radius=140.0000003624 / 2)
    extrude(amount=-350, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY.offset(400)) as cbore5_narrow:
        with Locations(Location((0.000000, 860.000000))):
            Circle(radius=59.99999501 / 2)
    extrude(amount=-400, mode=Mode.SUBTRACT)

    # 4 more counterbore holes at 60°, 120°, 180°, 240° CW from (0, 860, 400)
    with BuildSketch(Plane.XY.offset(400)) as cbore_pat_wide:
        for (_px, _py) in _pat_centres:
            with Locations(Location((_px, _py))):
                Circle(radius=140.0000003624 / 2)
    extrude(amount=-350, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY.offset(400)) as cbore_pat_narrow:
        for (_px, _py) in _pat_centres:
            with Locations(Location((_px, _py))):
                Circle(radius=59.99999501 / 2)
    extrude(amount=-400, mode=Mode.SUBTRACT)

    # Solid cylinder: ⌀1405mm at (0,0), z=0 to z=50mm
    with BuildSketch(Plane.XY) as cyl_profile:
        Circle(radius=1405 / 2)
    extrude(amount=50)

    # Counterbore hole at (245, -154.99999985, 0): bottom face, axis parallel to Z, drilling +Z
    # Total depth=50.01mm, cb_diameter=59mm, cb_depth=25mm, thru_diameter=34.00000277mm
    with BuildSketch(Plane.XY) as cbore6_wide:
        with Locations(Location((245.000000, -154.99999985))):
            Circle(radius=59 / 2)
    extrude(amount=25, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY) as cbore6_narrow:
        with Locations(Location((245.000000, -154.99999985))):
            Circle(radius=34.00000277 / 2)
    extrude(amount=50.01, mode=Mode.SUBTRACT)

    # Three more counterbore holes on bottom face, same spec as cbore6
    with BuildSketch(Plane.XY) as cbore7_wide:
        for (_cx, _cy) in [
            (555.000000, -154.99999985),
            (555.000000,  154.99999985),
            (245.000000,  154.99999985),
        ]:
            with Locations(Location((_cx, _cy))):
                Circle(radius=59 / 2)
    extrude(amount=25, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY) as cbore7_narrow:
        for (_cx, _cy) in [
            (555.000000, -154.99999985),
            (555.000000,  154.99999985),
            (245.000000,  154.99999985),
        ]:
            with Locations(Location((_cx, _cy))):
                Circle(radius=34.00000277 / 2)
    extrude(amount=50.01, mode=Mode.SUBTRACT)

    # Two-rectangle revolve cut: ±40° about the negative-X / XZ plane (total 80°)
    # Profile radii: rect1 r=750→1366, z=0→655; rect2 r=518→1366, z=655→924
    # Start plane at 140° (= 180°−40°), revolve 80° CCW → covers 140°→220°
    _rev_plane = Plane(
        origin=Vector(0, 0, 0),
        x_dir=Vector(cos(radians(140)), sin(radians(140)), 0),
        z_dir=Vector(sin(radians(140)), -cos(radians(140)), 0),
    )
    with BuildSketch(_rev_plane) as rev_cut_profile:
        with BuildLine():
            Polyline(
                (750.00000002,   0.0),
                (1366.23782153,  0.0),
                (1366.23782153,  924.46546812),
                ( 518.13410367,  924.46546812),
                ( 518.13410367,  655.000000),
                (750.00000002,   655.000000),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z, revolution_arc=80, mode=Mode.SUBTRACT)

# ==============================================================================
#  EXPORT
# ==============================================================================

output_step = "basebot.step"
output_stl  = "basebot.stl"

export_step(part.part, output_step)
export_stl(part.part, output_stl)

print(f"STEP exported → {output_step}")
print(f"STL  exported → {output_stl}")
