#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
baseboxbody.py — Base Box Body Part
=====================================
Build123d script to model the base box body and export STL + STEP.
"""

from build123d import *

with BuildPart() as part:
    with BuildSketch(Plane.XY):
        with BuildLine():
            Polyline(
                (2193.99993896,  900.000000),
                ( 432.68573761,  900.000000),
                ( 244.00001332,  711.31425663),
                ( 244.00001159, -711.31425491),
                ( 432.68573761, -900.000000),
                (2193.99993896, -900.000000),
                close=True,
            )
        make_face()
    extrude(amount=50)

    with BuildSketch(Plane.XY):
        Circle(radius=1503.99995272 / 2)
    extrude(amount=50, mode=Mode.SUBTRACT)

    # Step 3: 50mm thick strip following all boundaries (hex edges + circular arc)
    with BuildSketch(Plane(origin=(0, 0, 50), x_dir=(1, 0, 0), z_dir=(0, 0, 1))):
        with BuildLine():
            Polyline(
                (2193.99993896,  900.000000),
                ( 432.68573761,  900.000000),
                ( 244.00001332,  711.31425663),
                ( 244.00001159, -711.31425491),
                ( 432.68573761, -900.000000),
                (2193.99993896, -900.000000),
                close=True,
            )
        make_face()
        Circle(radius=1503.99995272 / 2, mode=Mode.SUBTRACT)
        offset(amount=-50, mode=Mode.SUBTRACT)
    extrude(amount=605)

    # Step 4: Two ⌀469.99998998mm holes cut from front face (y=-900) to back face (y=+900)
    # Plane at y=-900, normal pointing +Y (into body)
    # local (u, v) → world (u, -900, -v)  [y_dir = z_dir×x_dir = (0,1,0)×(1,0,0) = (0,0,-1)]
    front_plane = Plane(origin=(0, -900, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    with BuildSketch(front_plane):
        with Locations(
            (1278.99999358, -299.99999898),   # → world (1278.99999358, -900, 299.99999898)
            (1828.99999564, -299.99999898),   # → world (1828.99999564, -900, 299.99999898)
        ):
            Circle(radius=469.99998998 / 2)
    extrude(amount=1800, mode=Mode.SUBTRACT)

    # Step 5: Counterbore holes on front face (y=-900)
    # Centres: (1076.9999998, -900, 502.00000108) and (1076.9999998, -900, 98.0000005)
    # local (u, v) → world (u, -900, -v)  →  v = -502.00000108 and v = -98.0000005
    # CB pocket: ⌀58.99998823mm, 25mm deep
    with BuildSketch(front_plane):
        with Locations(
            (1076.9999998,                                 -502.00000108),
            (1076.9999998,                                  -98.0000005),
            (1076.9999998 + 404.0000029,                   -502.00000108),
            (1076.9999998 + 404.0000029,                    -98.0000005),
            (1076.9999998 + 550.00000206,                  -502.00000108),
            (1076.9999998 + 550.00000206,                   -98.0000005),
            (1076.9999998 + 404.0000029 + 550.00000206,    -502.00000108),
            (1076.9999998 + 404.0000029 + 550.00000206,     -98.0000005),
        ):
            Circle(radius=58.99998823 / 2)
    extrude(amount=25, mode=Mode.SUBTRACT)

    # Through-hole shaft: ⌀34.00000116mm, full 50mm depth
    with BuildSketch(front_plane):
        with Locations(
            (1076.9999998,                                 -502.00000108),
            (1076.9999998,                                  -98.0000005),
            (1076.9999998 + 404.0000029,                   -502.00000108),
            (1076.9999998 + 404.0000029,                    -98.0000005),
            (1076.9999998 + 550.00000206,                  -502.00000108),
            (1076.9999998 + 550.00000206,                   -98.0000005),
            (1076.9999998 + 404.0000029 + 550.00000206,    -502.00000108),
            (1076.9999998 + 404.0000029 + 550.00000206,     -98.0000005),
        ):
            Circle(radius=34.00000116 / 2)
    extrude(amount=50, mode=Mode.SUBTRACT)

    # Step 6: Mirror all 8 counterbore holes onto back face (y=+900) — mirror of XZ plane
    # Plane at y=+900, normal pointing -Y (into body)
    # local (u, v) → world (u, 900, v)  [y_dir = z_dir×x_dir = (0,-1,0)×(1,0,0) = (0,0,1)]
    back_plane = Plane(origin=(0, 900, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))

    # CB pocket: ⌀58.99998823mm, 25mm deep
    with BuildSketch(back_plane):
        with Locations(
            (1076.9999998,                                  502.00000108),
            (1076.9999998,                                   98.0000005),
            (1076.9999998 + 404.0000029,                    502.00000108),
            (1076.9999998 + 404.0000029,                     98.0000005),
            (1076.9999998 + 550.00000206,                   502.00000108),
            (1076.9999998 + 550.00000206,                    98.0000005),
            (1076.9999998 + 404.0000029 + 550.00000206,     502.00000108),
            (1076.9999998 + 404.0000029 + 550.00000206,      98.0000005),
        ):
            Circle(radius=58.99998823 / 2)
    extrude(amount=25, mode=Mode.SUBTRACT)

    # Through-hole shaft: ⌀34.00000116mm, full 50mm depth
    with BuildSketch(back_plane):
        with Locations(
            (1076.9999998,                                  502.00000108),
            (1076.9999998,                                   98.0000005),
            (1076.9999998 + 404.0000029,                    502.00000108),
            (1076.9999998 + 404.0000029,                     98.0000005),
            (1076.9999998 + 550.00000206,                   502.00000108),
            (1076.9999998 + 550.00000206,                    98.0000005),
            (1076.9999998 + 404.0000029 + 550.00000206,     502.00000108),
            (1076.9999998 + 404.0000029 + 550.00000206,      98.0000005),
        ):
            Circle(radius=34.00000116 / 2)
    extrude(amount=50, mode=Mode.SUBTRACT)

    # Step 7: Centre-to-centre slot cut from x=0 to x=850mm
    # Centers: (0, +75.00000236, 149.9999979) and (0, -75.00000154, 150.00000021)
    # Slot width: 200.00000017mm
    # Sketch plane at x=0: local (u,v) → world (0, u, v)
    slot_plane = Plane(origin=(0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    with BuildSketch(slot_plane):
        # Two semicircular ends
        with Locations(
            ( 75.00000236, 149.9999979),
            (-75.00000154, 150.00000021),
        ):
            Circle(radius=200.00000017 / 2)
        # Connecting rectangle (150mm along Y, 200mm along Z)
        with Locations((0.00000041, 150.00000005)):
            Rectangle(150.00000390, 200.00000017)
    extrude(amount=850, mode=Mode.SUBTRACT)

    # Step 8: Boss ⌀80.00000732mm at (770, -299.99999971, 557.49999995), extruded 72mm in -X
    boss_plane = Plane(
        origin=(770.000000, -299.99999971, 557.49999995),
        x_dir=(0, 1, 0),
        z_dir=(-1, 0, 0),
    )
    with BuildSketch(boss_plane):
        Circle(radius=80.00000732 / 2)
    extrude(amount=72, taper=-73.73980357 / 2)

    # Step 9: ⌀44.00000155mm through-hole from centre of boss
    with BuildSketch(boss_plane):
        Circle(radius=44.00000155 / 2)
    extrude(amount=850, mode=Mode.SUBTRACT)

    # Step 10: Same boss + hole, 360.00000159mm below (z = 557.49999995 - 360.00000159 = 197.49999836)
    boss_plane_2 = Plane(
        origin=(770.000000, -299.99999971, 557.49999995 - 360.00000159),
        x_dir=(0, 1, 0),
        z_dir=(-1, 0, 0),
    )
    with BuildSketch(boss_plane_2):
        Circle(radius=80.00000732 / 2)
    extrude(amount=72, taper=-73.73980357 / 2)

    with BuildSketch(boss_plane_2):
        Circle(radius=44.00000155 / 2)
    extrude(amount=850, mode=Mode.SUBTRACT)

    # Step 11: Mirror both bosses + holes about ZX plane (y → +299.99999971)
    boss_plane_3 = Plane(
        origin=(770.000000, +299.99999971, 557.49999995),
        x_dir=(0, 1, 0),
        z_dir=(-1, 0, 0),
    )
    with BuildSketch(boss_plane_3):
        Circle(radius=80.00000732 / 2)
    extrude(amount=72, taper=-73.73980357 / 2)

    with BuildSketch(boss_plane_3):
        Circle(radius=44.00000155 / 2)
    extrude(amount=850, mode=Mode.SUBTRACT)

    boss_plane_4 = Plane(
        origin=(770.000000, +299.99999971, 557.49999995 - 360.00000159),
        x_dir=(0, 1, 0),
        z_dir=(-1, 0, 0),
    )
    with BuildSketch(boss_plane_4):
        Circle(radius=80.00000732 / 2)
    extrude(amount=72, taper=-73.73980357 / 2)

    with BuildSketch(boss_plane_4):
        Circle(radius=44.00000155 / 2)
    extrude(amount=850, mode=Mode.SUBTRACT)

    # Step 12: Three rounded rectangles, extruded from z=50 up to z=100 (50mm tall pads)
    # Diagonal corners given at z=100; sketch at z=50 with +Z normal (local u,v = world X,Y)
    # Rect 1: corners (1250, 120.00076978) and (2050.03006987, 40)
    #   → centre (1650.01503494, 80.00038489), size 800.03006987 × 80.00076978
    # Rect 2: corners (1250, -79.99172884) and (1380.03006987, -160)
    #   → centre (1315.01503494, -119.99586442), size 130.03006987 × 80.00827116
    # Rect 3: corners (1540, -79.99857375) and (2000.03006987, -160)
    #   → centre (1770.01503494, -119.99928688), size 460.03006987 × 80.00142625
    with BuildSketch(Plane(origin=(0, 0, 50), x_dir=(1, 0, 0), z_dir=(0, 0, 1))):
        with Locations((1650.01503494, 80.00038489)):
            RectangleRounded(800.03006987, 80.00076978, 29.99988536)
        with Locations((1315.01503494, -119.99586442)):
            RectangleRounded(130.03006987, 80.00827116, 29.99988536)
        with Locations((1770.01503494, -119.99928688)):
            RectangleRounded(460.03006987, 80.00142625, 29.99988536)
    extrude(amount=50)

    # Step 13: Rectangle + circle extrude-cut on right face (x=2193.99993896), 50mm deep in -X
    # Plane: origin=(2193.99993896,0,0), x_dir=(0,1,0), z_dir=(-1,0,0)
    # local (u, v) → world (2193.99993896, u, -v)
    right_face_plane = Plane(origin=(2193.99993896, 0, 0), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))
    with BuildSketch(right_face_plane):
        # Rectangle: world Y [-188.8999939, -38.90000105], world Z [105, 240]
        # → local centre (-113.89999748, -172.5), size 149.99999285 × 135
        with Locations((-113.89999748, -172.5)):
            Rectangle(149.99999285, 135)
        # Circle: world (2193.99993896, 465, 169.99999893) → local (465, -169.99999893)
        with Locations((465, -169.99999893)):
            Circle(radius=85.00000099 / 2)
    extrude(amount=50, mode=Mode.SUBTRACT)

    # Step 14: Triangle extruded from y=-750 to y=-850 (100mm in -Y)
    # Plane at y=-750, normal -Y; local (u, v) → world (u, -750, v)
    tri_plane = Plane(origin=(0, -750, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
    with BuildSketch(tri_plane):
        with BuildLine():
            Polyline(
                (2143.99993896, 505.00007163),
                (2143.99993896, 655.000000),
                (1993.99997579, 655.000000),
                close=True,
            )
        make_face()
    extrude(amount=100)

    # Step 15: Pentagon cut from z=602.99999237 to z=630 (27.00000763mm in +Z)
    # Plane at z=602.99999237, normal +Z; local (u,v) → world (u, v, 602.99999237)
    with BuildSketch(Plane(origin=(0, 0, 602.99999237), x_dir=(1, 0, 0), z_dir=(0, 0, 1))):
        with BuildLine():
            Polyline(
                (2018.99998306, -829.01184082),
                (2100.74996948, -829.01184082),
                (2117.500000,   -800.000000  ),
                (2100.74996948, -770.98815918),
                (2018.99998198, -770.98815918),
                close=True,
            )
        make_face()
    extrude(amount=27.00000763, mode=Mode.SUBTRACT)

    # Step 16: ⌀33.99999754mm hole from z=655 down to z=505.00007163 (149.99992837mm deep)
    # Plane at z=655, normal -Z; local (u, v) → world (u, -v, 655)
    # Circle centre world (2084.00000097, -800, 655) → local (2084.00000097, 800)
    with BuildSketch(Plane(origin=(0, 0, 655), x_dir=(1, 0, 0), z_dir=(0, 0, -1))):
        with Locations((2084.00000097, 800.000000)):
            Circle(radius=33.99999754 / 2)
    extrude(amount=149.99992837, mode=Mode.SUBTRACT)

    # Step 17: Mirror triangle, pentagon cut, and hole about XZ plane (y → -y)

    # --- Mirrored triangle: y=+750 extruded to y=+850 (100mm in +Y) ---
    # Plane at y=+750, normal +Y; local (u,v) → world (u, 750, -v)
    tri_mirror_plane = Plane(origin=(0, 750, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    with BuildSketch(tri_mirror_plane):
        with BuildLine():
            Polyline(
                (2143.99993896, -505.00007163),
                (2143.99993896, -655.000000),
                (1993.99997579, -655.000000),
                close=True,
            )
        make_face()
    extrude(amount=100)

    # --- Mirrored pentagon cut: same z-plane, all Y coords negated ---
    with BuildSketch(Plane(origin=(0, 0, 602.99999237), x_dir=(1, 0, 0), z_dir=(0, 0, 1))):
        with BuildLine():
            Polyline(
                (2018.99998306,  829.01184082),
                (2100.74996948,  829.01184082),
                (2117.500000,    800.000000  ),
                (2100.74996948,  770.98815918),
                (2018.99998198,  770.98815918),
                close=True,
            )
        make_face()
    extrude(amount=27.00000763, mode=Mode.SUBTRACT)

    # --- Mirrored hole: centre world (2084.00000097, +800, 655) ---
    # Same plane (z=655, normal -Z); local (u,v)→world(u,-v,655)
    # world Y=+800 → -v=800 → v=-800 → local (2084.00000097, -800)
    with BuildSketch(Plane(origin=(0, 0, 655), x_dir=(1, 0, 0), z_dir=(0, 0, -1))):
        with Locations((2084.00000097, -800.000000)):
            Circle(radius=33.99999754 / 2)
    extrude(amount=149.99992837, mode=Mode.SUBTRACT)

    # Step 18: Six ⌀34mm circles with 13mm outer rings at z=80, extruded to z=50
    # Plane at z=80, normal -Z; local (u,v) → world (u, -v, 80)  (Y is negated)
    ring_plane = Plane(origin=(0, 0, 80), x_dir=(1, 0, 0), z_dir=(0, 0, -1))
    ring_locs = [
        (1956.96399657,  240.84000075),   # world (1956.96399657, -240.84000075, 80)
        (1969.66000299, -241.80099969),   # world (1969.66000299, +241.80099969, 80)
        (1449.00000097,   88.44000024),   # world (1449.00000097,  -88.44000024, 80)
        (1449.00000097, -190.99999936),   # world (1449.00000097, +190.99999936, 80)
        (1207.66000626,  240.84000075),   # world (1207.66000626, -240.84000075, 80)
        (1144.20000393, -241.80099969),   # world (1144.20000393, +241.80099969, 80)
    ]

    # Annular rings: outer r=30mm, inner r=17mm, extruded 30mm (z=80 → z=50)
    with BuildSketch(ring_plane):
        with Locations(*ring_locs):
            Circle(radius=30)
        with Locations(*ring_locs):
            Circle(radius=17, mode=Mode.SUBTRACT)
    extrude(amount=30)

    # Through holes ⌀34mm cut from z=80 downward through full body
    with BuildSketch(ring_plane):
        with Locations(*ring_locs):
            Circle(radius=17)
    extrude(amount=100, mode=Mode.SUBTRACT)

    # Step 19: Triangle from z=655 down to z=595.00000512 (59.99999488mm in -Z)
    # Plane at z=655, normal -Z; local (u,v) → world (u, -v, 655)
    with BuildSketch(Plane(origin=(0, 0, 655), x_dir=(1, 0, 0), z_dir=(0, 0, -1))):
        with BuildLine():
            Polyline(
                (453.39641571, -850.000000  ),
                (332.99684975, -729.60047219),
                (453.39641571, -661.54041797),
                close=True,
            )
        make_face()
    extrude(amount=59.99999488)

    # Step 20: Triangular prism — built directly from world vertices to avoid OCCT
    # boolean failure that can occur with tilted-plane sketch+extrude.
    # Extrusion direction: -(1,0,-1)/√2 × 84mm  →  shift = (-84/√2, 0, +84/√2)
    _d = 84.0 / (2.0 ** 0.5)            # ≈ 59.397mm
    _V1 = Vector(453.39641571, 661.54041797, 595.00000512)
    _V2 = Vector(332.99684975, 729.60047219, 474.60044098)
    _V3 = Vector(453.39641571, 850.00000000, 595.00001611)
    _shift = Vector(-_d, 0.0, _d)
    _V4, _V5, _V6 = _V1 + _shift, _V2 + _shift, _V3 + _shift
    _w1 = Wire.make_polygon([_V1, _V2, _V3])
    _w2 = Wire.make_polygon([_V4, _V5, _V6])
    _loft_solid = Solid.make_loft([_w1, _w2])
    # Pre-cut ⌀33.99999404mm hole through the loft before adding to avoid the
    # disconnected-compound issue where a later SUBTRACT may not reach a floating solid.
    # Hole: centre (394.00000231, 750, 655), direction -Z, depth 180.39955902mm → z=474.60044098
    _hole_cyl = Solid.make_cylinder(
        33.99999404 / 2,
        180.39955902,
        plane=Plane(origin=(394.00000231, 750.0, 655.0), x_dir=(1, 0, 0), z_dir=(0, 0, -1)),
    )
    add(_loft_solid.cut(_hole_cyl))

    # Step 21: Pentagon cut from z=601.50001526 to z=628.49998474 (26.99996948mm in +Z)
    # All vertices at z=601.50001526; local (u,v) → world (u, v, 601.50001526)
    with BuildSketch(Plane(origin=(0, 0, 601.50001526), x_dir=(1, 0, 0), z_dir=(0, 0, 1))):
        with BuildLine():
            Polyline(
                (453.39641571, 720.98815918),
                (377.24998474, 720.98815918),
                (360.49999237, 750.000000  ),
                (377.24998474, 779.01184082),
                (453.39641571, 779.01184082),
                close=True,
            )
        make_face()
    extrude(amount=26.99996948, mode=Mode.SUBTRACT)

    # Step 22: ⌀33.99999404mm hole from z=655 down to z=474.60044098 (180.39955902mm)
    # Plane at z=655, normal -Z; local (u,v) → world (u, -v, 655)
    # Centre world (394.00000231, 750, 655) → local (394.00000231, -750)
    with BuildSketch(Plane(origin=(0, 0, 655), x_dir=(1, 0, 0), z_dir=(0, 0, -1))):
        with Locations((394.00000231, -750.000000)):
            Circle(radius=33.99999404 / 2)
    extrude(amount=180.39955902, mode=Mode.SUBTRACT)

    # ── Mirror of Steps 19–22 about XZ plane (negate all Y coords) ──

    # Step 19m: Mirrored triangle (Y negated) from z=655 down 59.99999488mm
    # Plane at z=655, normal -Z; local (u,v) → world (u, -v, 655)
    # Original local Y: -850, -729.6, -661.5 → mirrored local Y: +850, +729.6, +661.5
    with BuildSketch(Plane(origin=(0, 0, 655), x_dir=(1, 0, 0), z_dir=(0, 0, -1))):
        with BuildLine():
            Polyline(
                (453.39641571,  850.000000  ),
                (332.99684975,  729.60047219),
                (453.39641571,  661.54041797),
                close=True,
            )
        make_face()
    extrude(amount=59.99999488)

    # Step 20m: Mirrored loft (Y negated)
    _V1m = Vector(453.39641571, -661.54041797, 595.00000512)
    _V2m = Vector(332.99684975, -729.60047219, 474.60044098)
    _V3m = Vector(453.39641571, -850.00000000, 595.00001611)
    _V4m, _V5m, _V6m = _V1m + _shift, _V2m + _shift, _V3m + _shift
    _w1m = Wire.make_polygon([_V1m, _V2m, _V3m])
    _w2m = Wire.make_polygon([_V4m, _V5m, _V6m])
    _loft_solid_m = Solid.make_loft([_w1m, _w2m])
    _hole_cyl_m = Solid.make_cylinder(
        33.99999404 / 2,
        180.39955902,
        plane=Plane(origin=(394.00000231, -750.0, 655.0), x_dir=(1, 0, 0), z_dir=(0, 0, -1)),
    )
    add(_loft_solid_m.cut(_hole_cyl_m))

    # Step 21m: Mirrored pentagon cut (Y negated)
    with BuildSketch(Plane(origin=(0, 0, 601.50001526), x_dir=(1, 0, 0), z_dir=(0, 0, 1))):
        with BuildLine():
            Polyline(
                (453.39641571, -720.98815918),
                (377.24998474, -720.98815918),
                (360.49999237, -750.000000  ),
                (377.24998474, -779.01184082),
                (453.39641571, -779.01184082),
                close=True,
            )
        make_face()
    extrude(amount=26.99996948, mode=Mode.SUBTRACT)

    # Step 22m: Mirrored hole (Y negated)
    # World centre (394.00000231, -750, 655) → local on z=655 -Z plane: (394.00000231, +750)
    with BuildSketch(Plane(origin=(0, 0, 655), x_dir=(1, 0, 0), z_dir=(0, 0, -1))):
        with Locations((394.00000231, 750.000000)):
            Circle(radius=33.99999404 / 2)
    extrude(amount=180.39955902, mode=Mode.SUBTRACT)

    # Step 23: Two ⌀60.00000372mm through holes along Z axis
    # Centres: (790, -455, 50.00063903) and (790, 455, 50.00063903)
    # Cut from z=0 through full height (655mm)
    with BuildSketch(Plane.XY):
        with Locations(
            (790.000000, -455.000000),
            (790.000000,  455.000000),
        ):
            Circle(radius=60.00000372 / 2)
    extrude(amount=655, mode=Mode.SUBTRACT)

    # Step 24: 1504mm diameter circular cut extruded up to 670mm
    with BuildSketch(Plane.XY):
        Circle(radius=1504 / 2)
    extrude(amount=670, mode=Mode.SUBTRACT)

export_step(part.part, "baseboxbody.step")
export_stl(part.part, "baseboxbody.stl")

print("STEP exported → baseboxbody.step")
print("STL  exported → baseboxbody.stl")
