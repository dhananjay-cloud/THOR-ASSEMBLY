# Art3Body Parametric Build123d Model

This folder contains a parametric build123d reconstruction of `Art3Body`.
The main script is:

```text
Art3Body_parametric.py
```

It generates:

```text
Art3Body_main_dome_parametric.step
Art3Body_main_dome_parametric.stl
```

and validates the generated STL against:

```text
Art3Body.stl
```

## Run

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art3Body_main_dome_parametric.py
```

If Python tries to write bytecode into a protected cache folder:

```bash
PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art3Body_main_dome_parametric.py
```

## Requirements

The CAD build needs `build123d`. Validation uses `trimesh`, `numpy`, and
`scipy`.

```bash
python3 -m pip install --user build123d trimesh numpy scipy
```

Exact boolean symmetric-difference validation needs watertight meshes and a
boolean backend available to trimesh.

## What The Code Does

The script builds Art3Body as editable analytic CAD geometry rather than
importing or remeshing the reference STL.

The build sequence is:

1. Create the circular base flange.
2. Cut the underside base recess.
3. Cut the bottom circular-plus-rectangular profile.
4. Cut the four stepped through-holes in the base flange.
5. Add the main capsule body and lofted upper dome.
6. Subtract the hollow interior with a separate inner capsule and inner dome.
7. Add the back circular mounting feature, arched slot, counterbores, hex cuts,
   and rectangular boss cuts.
8. Add the three top dome vent slots.
9. Add the front inner pads and front through-holes.
10. Add the internal side pads, slotted panels, square recesses, and local cuts.
11. Export STEP and STL.
12. Validate the generated STL against the reference STL.

## Geometry Methodology

The main body is a capsule-column shell. In plan view, the footprint has a
straight center band and rounded left/right sides. The upper dome is generated
as a loft of XZ arc sections across Y stations, which lets the crown and side
seam follow the curved section views.

The hollow interior is not made with a simple shell command. It is subtracted as
a separately lofted void, giving independent control of:

```text
outer dome curvature
inner roof curvature
wall thickness
inner side seam height
bottom opening height
```

The loft end stations are kept just inside the exact capsule limit with:

```text
capsule_loft_end_fraction = 0.999
inner_capsule_loft_end_fraction = 0.999
```

This avoids zero-area STL triangles at the front/back dome seams while keeping
the visible geometry essentially unchanged.

Most secondary details are built with named primitive cutters:

```text
z_axis_cylinder
y_axis_cylinder
x_axis_cylinder
z_axis_box
y_axis_box
x_axis_capsule_slot
z_axis_capsule_slot
y_axis_hex_prism
```

## Major Feature Groups

### Base Flange

The circular base flange has:

```text
radius: 550.5
height: 210
```

It includes four stepped through-holes at:

```text
( 225,  390)
(-225,  390)
( 225, -390)
(-225, -390)
```

Each uses:

```text
through radius: 17
through Z range: 70 to 210
counterbore radius: 29.5
counterbore Z range: 180 to 210
```

### Dome And Shell

The outer dome is lofted from Y-station arc sections. The internal hollow is
subtracted with a separate loft. This is the main method used to match the dome
curvature from the sectional reference views.

### Back Face

The back face includes:

```text
large tapered circular pad
R82 counterbore cut
R50 central through bore
arched relief slot with rounded ends
vertical rectangular slot through the boss
small side holes
inner hexagonal cuts around the arc-slot end holes
```

### Front And Inner Features

The front face includes:

```text
three R17 through-holes
one R50 through-hole
three raised internal pads with local notches
```

The side/internal walls include:

```text
left internal bracket pad
upper side panel with four vertical slots
400 x 400 square inward cut
opposite curved-wall profile with chamfered returns and lower holes
```

### Dome Vents

The top dome has three rounded slots cut through the dome surface. These are
created with horizontal capsule-slot cutters projected through the dome volume.

## Validation Methodology

After exporting, the script loads the generated STL and reference STL. It
reports:

```text
watertightness
face counts
bounding boxes
raw volume difference
auto-scaled reference volume difference
two-way symmetric surface-distance statistics
surface-area weighted symmetric-difference volume proxy
exact boolean symmetric-difference volume
```

The supplied `Art3Body.stl` is about 10x smaller than the build123d model in
linear units. The script prints raw values first, then auto-scales the reference
mesh for comparison using the bounding-box diagonal. This does not modify the
reference file.

The approximate symmetric-difference volume proxy is computed as:

```text
0.5 * (generated_area * mean_distance_to_reference
     + reference_area * mean_distance_to_generated)
```

The exact boolean symmetric difference is attempted after that. It now runs
because the generated STL is watertight.

## Current Validation Output

Latest run:

```text
Generated watertight: True
Reference watertight:  True
Generated faces: 34,244
Reference faces:  34,354

Generated bbox:
min=(-550.500, -550.329, 0.000)
max=(550.500, 550.329, 1525.000)
extents=(1101.000, 1100.658, 1525.000)

Reference bbox:
min=(-55.050, -55.041, 0.000)
max=(55.050, 55.041, 152.497)
extents=(110.100, 110.083, 152.497)

Generated volume: 276,073,355.376 cubic mm
Reference volume:  277,881.104 cubic mm
Raw volume delta: 275,795,474.272 cubic mm (99249.452%)

Reference auto-scale for comparison: 9.999703x
Scaled reference volume: 277,856,333.978 cubic mm
Scaled volume delta:    -1,782,978.602 cubic mm (-0.642%)

Approximate symmetric surface distance (50,000 samples each way):
generated -> reference: mean=72.645 mm, median=50.182 mm, p95=222.578 mm, max=301.699 mm
reference -> generated: mean=38.761 mm, median=29.096 mm, p95=110.817 mm, max=269.268 mm

Symmetric surface-distance mean: 55.703 mm
p95 envelope: 222.578 mm
Approximate symmetric-difference volume proxy: 576,433,689.623 cubic mm
Boolean symmetric-difference volume: 5,130,795.726 cubic mm
```

The scaled volume delta is currently about `-0.642%`. The boolean symmetric
difference is now available because the generated STL is watertight.

## Notes

All dimensions in the parametric model are in millimeters at `SCALE = 1.0`.
The validation auto-scale is only for comparing against `Art3Body.stl`, whose
linear units are approximately 10x smaller.
