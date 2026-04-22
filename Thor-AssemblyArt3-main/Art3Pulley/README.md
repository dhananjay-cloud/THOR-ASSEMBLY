# Art3Pulley Parametric Model

This folder contains a build123d reconstruction of the Art3Pulley geometry.
The main parametric version is:

```text
Art3Pulley_parametric_pure.py
```

It generates:

```text
Art3Pulley_parametric_pure.step
Art3Pulley_parametric_pure.stl
```

## Purpose

`Art3Pulley_parametric_pure.py` builds the pulley directly from named
parameters, arcs, lines, pockets, bores, and cut profiles. The script does not
import DXF files at runtime. The important profile dimensions that were
previously extracted from DXF/STEP references are now baked into the script as
editable parametric data.

## Requirements

Install the CAD/export dependencies:

```bash
python3 -m pip install --user build123d cadquery trimesh manifold3d scipy ocp-vscode
```

`ocp-vscode` is optional. The script currently has viewer launching disabled,
so it can run headlessly and just export the CAD files.

## Run

From any directory:

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art3Pulley_parametric_pure.py
```

If Python tries to write bytecode into a protected cache folder, run:

```bash
PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art3Pulley_parametric_pure.py
```

## Outputs

The script writes exports to:

```text
/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d
```

Generated files:

```text
Art3Pulley_parametric_pure.step
Art3Pulley_parametric_pure.stl
```

The script also compares the generated model against:

```text
Art3Pulley-faces.step
Art3Pulley.stl
```

when those reference files are present.

## Main Parameters

All dimensions are in millimeters.

Key body parameters:

```python
rim_radius      = 370.0
total_height    = 180.0
sphere_radius   = 400.281
sphere_z_centre = 15.0
lower_height    = 30.0
```

Central bore and bottom pocket:

```python
hub_bore_r                 = 50.0
bottom_center_pocket_r     = 82.0
bottom_center_pocket_depth = 90.0
```

Fixing holes:

```python
fix_hole_positions = [(0, -180), (-160, 130), (160, 130)]
fix_cbore_r        = 29.5
fix_bore_r         = 17.0
fix_cbore_depth    = 30.0
```

Keyway/bracket:

```python
arm_x_half     = 115.0
arm_y_start    = 195.0
arm_y_end      = 230.0
arm_height     = 130.0

kw_x_half      = 29.012
kw_y_inner     = 243.5
kw_y_outer     = 273.5
kw_rect_top_z  = 81.75
kw_slope_top_z = 98.5
kw_bore_r      = 17.0
kw_bore_z      = 65.0
```

Central rectangular notches at the `r=50` bore:

```python
central_notch_x_outer = 80.9881496429443
central_notch_y_half  = 16.749999434163
central_notch_z1      = 70.0
central_notch_z2      = 90.0
```

Bottom cut depths:

```python
bottom_middle_cut_depth    = 40.0
bottom_remaining_cut_depth = 130.0
```

## Profile Data

The top web openings are controlled by:

```python
top_web_segments
```

Each segment is either:

```python
("line", x1, y1, x2, y2)
("arc", cx, cy, radius, start_angle_deg, end_angle_deg)
```

The bottom middle profile is controlled by:

```python
bottom_middle_profile
```

Each entry is:

```python
(x, y, bulge)
```

The deeper bottom/keyway-side relief is controlled by:

```python
bottom_remaining_segments
_bottom_remaining_clean_loops()
```

These profiles replace the earlier runtime DXF imports.

## Current Validation

The latest generated pure-parametric model reported:

```text
CAD volume       : 52,247,459.4104 mm3
Delta vs STEP    : -0.4385 %
STL vs CAD       : -0.0629 %
STL vs reference : -0.1551 %
CAD sym-diff     : 0.6103 %
STL sym-diff     : 0.3162 %
```

The generated STL is post-processed after export with a conservative mesh
cleanup: degenerate triangles are removed, near-identical seam vertices are
merged, and normals are fixed. It does not rebuild or cap the keyway-side
bottom profile. The current export reports `watertight=True` and
`is_volume=True`, so STL symmetric-difference validation runs successfully. CAD
symmetric difference from STEP/OCP booleans is still reported as the primary
geometry comparison.

## Methodology

The model was reconstructed as a build123d parametric script instead of using
an import/export wrapper. The final script creates the CAD body from primitive
solids, named dimensions, and source-derived profile segments.

The workflow used was:

1. Build the main pulley body from simple solids:

```text
lower spherical lip + upper cylindrical rim
```

2. Add/remove major functional features:

```text
top web openings
central through bore
bottom Ø164 x 90 pocket
fixing holes
side counterbores
keyway/bracket cuts
bottom relief cuts
central bore notches
radial r=17 bore
```

3. Replace runtime DXF imports with hardcoded parametric segment definitions.
   The segment definitions are still editable, but the script no longer reads
   DXF files while generating the part.

4. Export the generated CAD model as STEP.

5. Export the generated STEP as STL through CadQuery.

6. Compare the generated model against the available reference STEP/STL files.

## Volume Difference

The CAD volume is taken directly from the build123d solid:

```python
_step_vol = result.volume
```

If the reference STEP file exists, it is imported and its CAD volume is also
read:

```python
_ref_step = import_step(REFERENCE_STEP_PATH)
_ref_step.volume
```

The percentage difference is calculated as:

```text
CAD delta (%) = (generated CAD volume - reference STEP volume)
                / reference STEP volume * 100
```

So:

```text
positive value = generated model has more material than reference
negative value = generated model has less material than reference
```

The generated STL is also checked against the generated CAD volume:

```text
Gen vs CAD (%) = (generated STL mesh volume - generated CAD volume)
                 / generated CAD volume * 100
```

This tells whether STL tessellation/export preserved the CAD volume closely.
A small value near zero means the STL export is faithful to the CAD model.

## Symmetric Difference

The script now calculates symmetric difference at CAD level first, using the
generated solid and the reference STEP solid. This avoids false failures from
non-watertight STL tessellation.

The CAD symmetric difference uses two boolean cuts:

```python
_cad_gen_only = result.cut(_ref_cad).volume
_cad_ref_only = _ref_cad.cut(result).volume
```

These mean:

```text
generated - reference = material present only in generated model
reference - generated = material missing from generated model
```

The CAD union volume is estimated from both equivalent union expressions:

```text
union = generated volume + reference-only volume
union = reference volume + generated-only volume
```

The script averages those two values for numerical stability:

```python
_cad_union_est = (
    (result.volume + _cad_ref_only)
    + (_ref_cad.volume + _cad_gen_only)
) / 2.0
```

Then:

```text
CAD symmetric difference (%) =
    (generated-only volume + reference-only volume)
    / estimated union volume * 100
```

A lower value means the generated CAD model is closer to the reference STEP.

## STL Symmetric Difference

STL symmetric difference measures how much material differs spatially between
the generated STL and the reference STL, but it requires both triangle meshes
to be valid boolean volumes.

It is calculated using boolean operations on meshes:

```python
_diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
_diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
_union   = trimesh.boolean.union([_gen, _ref], engine="manifold")
_sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100
```

Meaning:

```text
generated - reference = material present only in generated model
reference - generated = material missing from generated model
union                 = total occupied volume of both models combined
```

The final metric is:

```text
Symmetric difference (%) =
    (extra generated volume + missing generated volume)
    / union volume * 100
```

The pure-parametric script repairs the generated STL after export with a small
mesh cleanup only. It does not use a generic hole-fill, because generic hole
fills can hide real features. If either mesh is still not watertight or not a
valid volume, the script reports:

```text
STL sym-diff : [skipped — mesh is not a valid boolean volume]
```

That does not mean the CAD model failed. It means the STL tessellation is not
suitable for mesh booleans. In that case, use the CAD symmetric difference.

## STL Scaling Check

The reference STL may not be in the same unit scale as the generated model, so
the script compares bounding-box spans and estimates a scale factor:

```python
_spans_g = _gen.bounds[1] - _gen.bounds[0]
_spans_r = _ref_raw.bounds[1] - _ref_raw.bounds[0]
_scale = median(_spans_g / _spans_r)
```

The scale is rounded to the nearest quarter step:

```python
_scale = round(_scale * 4) / 4
```

If the scale differs noticeably from `1.0`, the reference mesh copy is scaled
before validation. In the current runs, the reference STL is reported as scaled
by `10.00`.

## Notes

- The original working script is still separate:

```text
/Users/softage/Downloads/Art3Pulley_parametric.py
```

- The pure-parametric script is intentionally separate so the earlier file is
  not overwritten.
- The model uses profile-derived numeric parameters; to change a feature, edit
  the named parameter or segment list rather than importing a new DXF.
