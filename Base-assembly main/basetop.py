#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
basetop.py — Base Top Part
===========================
Build123d script: revolves a closed 2D profile around the Z axis.
Profile points (a→h) are defined on the XZ plane and closed automatically.
"""

from build123d import *

# ==============================================================================
#  PROFILE COORDINATES  (x, z)  — Y=0 plane (XZ)
# ==============================================================================
# a(-749.9999974,  275.000000)
# b(-550.00000102, 275.000000)
# c(-550.00000102, 130.000000)
# d(-490.00000087, 130.000000)
# e(-490.00000087, 124.99999969)
# f(-575.68888193,  64.99999969)
# g(-575.68888193,   0.0)
# h(-749.9999974,    0.0)  → back to a (closed)

# ==============================================================================
#  GEOMETRY
# ==============================================================================

with BuildPart() as part:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine() as outline:
            Polyline(
                (-749.9999974,   275.000000),
                (-550.00000102,  275.000000),
                (-550.00000102,  130.000000),
                (-490.00000087,  130.000000),
                (-490.00000087,  124.99999969),
                (-575.68888193,   64.99999969),
                (-575.68888193,    0.0),
                (-749.9999974,     0.0),
                close=True,
            )
        make_face()
    revolve(axis=Axis.Z, revolution_arc=360)

    # Three equally spaced through-holes at 675.000000009 mm from centre
    with PolarLocations(radius=675.000000009, count=3):
        Hole(radius=33.999999098 / 2, depth=part.part.bounding_box().size.Z)

# ==============================================================================
#  EXPORT
# ==============================================================================

output_step = "basetop.step"
output_stl  = "basetop.stl"

export_step(part.part, output_step)
export_stl(part.part, output_stl)

print(f"STEP exported → {output_step}")
print(f"STL  exported → {output_stl}")
