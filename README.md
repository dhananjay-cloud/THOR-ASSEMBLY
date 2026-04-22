# Thor-AssemblyArt4

Parametric reconstruction of the [Thor Open-Source Robot Arm](https://github.com/AngelLM/Thor) assembly parts using **build123d** — a Python CAD kernel built on OpenCascade.

Each part is reverse-engineered from the original Fusion 360 mesh geometry via coordinate extraction, then rebuilt programmatically and validated against the original STL files. The final assembly is composed from all 10 parts using transformation data extracted from Fusion 360.

---

## Project Overview

| Detail | Info |
|---|---|
| **Assigned Repo** | [AngelLM/Thor](https://github.com/AngelLM/Thor) |
| **Submission Repo** | [Thor-AssemblyArt4](https://github.com/avajones081196/Thor-AssemblyArt4) |
| **Completion** | ✅ 10 parts + assembly complete |
| **Method** | Fusion 360 → CSV coordinates → build123d → STL/STEP → Validation → Assembly |

---

## Parts Progress

| # | Part Name | Completion | Vol. Diff (%) | Sym. Diff (%) | Time |
|---|---|---|---|---|---|
| 1 | Art4BearingFix | ✅ Done | 0.036% | 0.050% | 5 hrs |
| 2 | Art4BodyBot | ✅ Done | 0.030% | 0.037% | 4 hrs |
| 3 | Art4BodyFan | ✅ Done | 0.012% | 0.071% | 2 hrs |
| 4 | Art4Optodisk | ✅ Done | 0.003% | 0.251% | 1.5 hrs |
| 5 | Art4TransmissionColumn | ✅ Done | 0.428% | N/A* | 6 hrs |
| 6 | Art4BearingPlug | ✅ Done | 0.784% | 0.913% | 3 hrs |
| 7 | Art4BearingRing | ✅ Done | 0.002% | 0.140% | 1.5 hrs |
| 8 | Art4Body | ✅ Done | 0.056% | 0.375% | 9 hrs |
| 9 | Art4MotorFix | ✅ Done | 0.465% | 0.544% | 1.5 hrs |
| 10 | Art4MotorGear | ✅ Done | 0.286% | 0.370% | 3 hrs |
| — | Assembly | ✅ Done | — | — | 8 hrs |

**Total Time: 44.5 hours**

*\*Symmetric difference could not be computed for Part 5 because the original downloaded STL mesh is not watertight (`Mesh B watertight: False`). This is a property of the source mesh, not the reconstruction.*

*Note: Small volume differences (especially on circular features) are expected because the original STL uses faceted polygon approximations for circles, while build123d uses true mathematical circle geometry — making the reconstruction more geometrically accurate than the source mesh.*

---

## Assembly

The final assembly combines all 10 parts (12 instances total — Art4BearingFix and Art4BodyFan each appear twice, mirrored) into a single Thor Art4 robot arm joint module.

**Assembly approach:**
1. All 10 parts were first assembled in **Fusion 360** using Joints, Move, and Ground operations
2. A **Fusion API script** extracted the 4×4 transformation matrix (position + rotation) for each component instance
3. Two **build123d assembly scripts** recreate the assembly programmatically:
   - `assemble_step_files.py` — loads STEP files (exact B-Rep CAD geometry), applies transforms via `gp_Trsf.SetValues()`, exports combined STEP + STL
   - `assemble_stl_files.py` — loads STL files (mesh triangles), applies rotation matrices + translation via numpy, exports combined STL

**Why both STEP and STL assembly scripts?**
- **STEP assembly** produces clean CAD geometry with exact surfaces — ideal for further engineering work, simulations, and visual inspection in OCP viewer
- **STL assembly** produces a lightweight mesh — useful for 3D printing, quick visualization, and file sharing (496,712 triangles total)

**Component instances (12 total):**

| Instance | Part | Position (mm) | Rotation |
|---|---|---|---|
| Art4Body | Part 8 | (0, 0, −189.5) | Identity |
| Art4BodyBot | Part 2 | (0, 0, −194.0) | Identity |
| Art4MotorFix | Part 9 | (0, 0, −189.5) | Identity |
| Art4BearingRing | Part 7 | (0, 0, −205.84) | Identity |
| Art4TransmissionColumn | Part 5 | (0, 0, −270.0) | Rz = 21.6° |
| Art4MotorGear | Part 10 | (0, 0, −184.0) | Rz = 21.6° |
| Art4Optodisk | Part 4 | (0, 0, −206.0) | Rx=180° Rz=156.7° |
| Art4BearingPlug | Part 6 | (−35.9, 0, −200.8) | Rx=180° Rz=180° |
| Art4BodyFan (Left) | Part 3 | (−66.0, 0, −189.5) | Identity |
| Art4BodyFan (Right) | Part 3 | (66.0, 0, −189.5) | Rz = 180° |
| Art4BearingFix (Left) | Part 1 | (−51.0, 0, −89.5) | Rx=−90° Rz=90° |
| Art4BearingFix (Right) | Part 1 | (51.0, 0, −89.5) | Rx=−90° Rz=−90° |

---

## Methodology

The workflow follows a 5-stage pipeline:

```
Fusion 360 Mesh  →  CSV Extraction  →  build123d Reconstruction  →  STL Validation  →  Assembly
     (1)                (2)                    (3)                       (4)              (5)
```

### Stage 1 — Coordinate Extraction (Fusion 360)

A Fusion 360 Python script traverses the mesh body and exports vertex coordinates to CSV files. Each CSV captures a specific geometric feature:

- **Flat profiles** — Line segments forming closed outlines (base faces)
- **Triangular faces** — Vertex triplets defining mesh surfaces (top, sides)
- **Hole boundaries** — Line loops defining hole edges on curved surfaces
- **Circle profiles** — 3-point circle definitions or polygonal approximations
- **Hexagonal profiles** — Line-segment loops for bolt/nut pocket cuts
- **Arc profiles** — 3-point arc definitions for curved slot openings
- **Tooth profiles** — Closed polygon outlines of gear teeth at different Z planes
- **Revolution profiles** — Line + arc chains on YZ plane for revolve operations
- **D-shaped profiles** — Line + arc closed loops for loft-cut and tapered extrude operations

### Stage 2 — CSV Preprocessing (`0_preprocess_csvs.py`)

- Detects and merges split CSV files (e.g., `S2_1.csv`, `S2_2.csv` → `S2.csv`)
- Removes geometry-aware duplicates (direction-independent lines, rotation-independent triangles)
- Re-numbers steps sequentially
- Incremental mode — safe to re-run without reprocessing existing shapes

### Stage 3 — build123d Reconstruction

The reconstruction follows numbered guidelines, each building on the previous. Each part has its own guideline set tailored to the geometry. See individual part sections below for full guideline tables.

### Stage 4 — Validation (`*_compare_stl_files.py`)

Compares the build123d STL against the original downloaded from the Thor repo:

- **Volume comparison** — absolute difference + % error
- **Symmetric difference** — boolean intersection to measure spatial overlap
- **Bounding box check** — per-axis tolerance ±0.1mm
- **Summary scorecard** — automatic grading (Excellent / Good / Acceptable / Poor)

### Stage 5 — Assembly

- Fusion 360 assembly positions extracted via API script → `thor_assembly_transforms.txt`
- Transforms applied in build123d using OCP `gp_Trsf.SetValues()` (raw 3×3 rotation matrix + translation)
- Assembly exported as both STEP (CAD geometry) and STL (mesh)

---

## Part Results Summary

### Part 1: Art4BearingFix
```
🟢 EXCELLENT | Vol: 0.036% | Sym: 0.050% | Overlap: 99.99% | BB: ✅ PASS
Solid volume: 880.307 mm³ (original: 879.991 mm³)
```

### Part 2: Art4BodyBot
```
🟢 EXCELLENT | Vol: 0.030% | Sym: 0.037% | Overlap: 100.00% | BB: ✅ PASS
Solid volume: 43,401.296 mm³ (original: 43,384.240 mm³)
```

### Part 3: Art4BodyFan
```
🟢 EXCELLENT | Vol: 0.012% | Sym: 0.071% | Overlap: 99.97% | BB: ✅ PASS
Solid volume: 12,563.366 mm³ (original: 12,561.910 mm³)
```

### Part 4: Art4Optodisk
```
🟢 EXCELLENT | Vol: 0.003% | Sym: 0.251% | Overlap: 99.88% | BB: ✅ PASS
Solid volume: 8,853.517 mm³ (original: 8,853.255 mm³)
```

### Part 5: Art4TransmissionColumn
```
🟢 EXCELLENT | Vol: 0.428% | Sym: N/A* | BB: ✅ PASS
Solid volume: 78,084.016 mm³ (original: 78,419.464 mm³)
```

### Part 6: Art4BearingPlug
```
🟢 EXCELLENT | Vol: 0.784% | Sym: 0.913% | Overlap: 99.94% | BB: ✅ PASS
Solid volume: 239.415 mm³ (original: 237.553 mm³)
```

### Part 7: Art4BearingRing
```
🟢 EXCELLENT | Vol: 0.002% | Sym: 0.140% | Overlap: 99.93% | BB: ✅ PASS
Solid volume: 23,447.518 mm³ (original: 23,447.164 mm³)
```

### Part 8: Art4Body
```
🟢 EXCELLENT | Vol: 0.056% | Sym: 0.375% | Overlap: 99.85% | BB: ✅ PASS
Solid volume: 227,834.042 mm³ (original: 227,706.125 mm³)
Most complex part — 42 guidelines, 21 CSV shapes, 180° dome revolve,
tapered extrude-join, mirror operation across YZ plane.
```

### Part 9: Art4MotorFix
```
🟢 EXCELLENT | Vol: 0.465% | Sym: 0.544% | Overlap: 99.96% | BB: ✅ PASS
Solid volume: 3,787.859 mm³ (original: 3,770.317 mm³)
```

### Part 10: Art4MotorGear
```
🟢 EXCELLENT | Vol: 0.286% | Sym: 0.370% | Overlap: 99.96% | BB: ✅ PASS
Solid volume: 6,955.164 mm³ (original: 6,935.312 mm³)
Helical gear with mathematically perfect twisted sweep (+46.835°),
10-tooth circular pattern, 60 interpolation frames.
```

---

## Repository Structure

```
Thor-AssemblyArt4/
├── README.md
├── requirements.txt
│
├── 1_Art4BearingFix/
│   ├── csv_data_1_Art4BearingFix/
│   ├── csv_merged/
│   ├── 0_preprocess_csvs.py
│   ├── 1_1_Art4BearingFix_build123d.py
│   ├── 1_2_compare_stl_files.py
│   ├── 1_Art4BearingFix_original.stl
│   ├── 1_Art4BearingFix_build123d_G_1_9.stl
│   └── 1_Art4BearingFix_build123d_G_1_9.step
│
├── 2_Art4BodyBot/
│   ├── ...
│   ├── 2_Art4BodyBot_G_1_18.stl
│   └── 2_Art4BodyBot_G_1_18.step
│
├── 3_Art4BodyFan/
│   ├── ...
│   ├── 3_Art4BodyFan_G_1_7.stl
│   └── 3_Art4BodyFan_G_1_7.step
│
├── 4_Art4Optodisk/
│   ├── ...
│   ├── 4_Art4Optodisk_G_1_13.stl
│   └── 4_Art4Optodisk_G_1_13.step
│
├── 5_Art4TransmissionColumn/
│   ├── ...
│   ├── 5_Art4TransmissionColumn_G_1_16.stl
│   └── 5_Art4TransmissionColumn_G_1_16.step
│
├── 6_Art4BearingPlug/
│   ├── ...
│   ├── 6_Art4BearingPlug_G_1_9.stl
│   └── 6_Art4BearingPlug_G_1_9.step
│
├── 7_Art4BearingRing/
│   ├── ...
│   ├── 7_Art4BearingRing_G_1_14.stl
│   └── 7_Art4BearingRing_G_1_14.step
│
├── 8_Art4Body/
│   ├── ...
│   ├── 8_Art4Body_G_1_42.stl
│   └── 8_Art4Body_G_1_42.step
│
├── 9_Art4MotorFix/
│   ├── ...
│   ├── 9_Art4MotorFix_G_1_7.stl
│   └── 9_Art4MotorFix_G_1_7.step
│
├── 10_Art4MotorGear/
│   ├── ...
│   ├── 10_Art4MotorGear_G_1_15.stl
│   └── 10_Art4MotorGear_G_1_15.step
│
└── 1_10_Thor_AssemblyArt4/                 # Assembly folder
    ├── assemble_step_files.py              # STEP assembly script (build123d)
    ├── assemble_stl_files.py               # STL assembly script (numpy-stl)
    ├── thor_assembly_transforms.txt        # Fusion 360 transform data
    ├── requirements.txt
    ├── Thor_AssemblyArt4_STEP.step.zip     # ← Final STEP assembly (compressed — GitHub 100MB limit)
    ├── Thor_AssemblyArt4_STEP.stl          # ← STL from STEP assembly
    ├── Thor_AssemblyArt4_STL.stl           # ← STL mesh assembly
    ├── 1_Art4BearingFix_build123d_G_1_9.step
    ├── 1_Art4BearingFix_build123d_G_1_9.stl
    ├── 2_Art4BodyBot_G_1_18.step
    ├── 2_Art4BodyBot_G_1_18.stl
    ├── ... (all 10 part STEP + STL files)
    ├── 10_Art4MotorGear_G_1_15.step
    └── 10_Art4MotorGear_G_1_15.stl
```

---

## Setup & Usage

### Prerequisites

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### requirements.txt

```
build123d
ocp_vscode
numpy-stl
trimesh
manifold3d
```

### Running — Individual Parts

```bash
# 1. Preprocess CSVs
python 0_preprocess_csvs.py

# 2. Build the part (exports STL + STEP)
python 10_1_Art4MotorGear.py

# 3. Compare against original
python 10_2_compare_stl_files.py
```

### Running — Assembly

```bash
cd 1_10_Thor_AssemblyArt4/

# STEP assembly (CAD geometry — best quality)
python assemble_step_files.py

# STL assembly (mesh — lightweight)
python assemble_stl_files.py
```

---

## CSV Format

All coordinate files follow the same schema:

| Column | Description |
|---|---|
| Steps | Sequential row number |
| Draw Type | `Line`, `triangular_face_N`, `3_point_arc_N`, `3_point_circle_N`, `Point` |
| X1, Y1, Z1 | First point coordinates |
| X2, Y2, Z2 | Second point (or `NA`) |
| X3, Y3, Z3 | Third point (or `NA`) |

---

## Technologies

- **Fusion 360** — Source mesh geometry + coordinate extraction + assembly positioning
- **build123d** — Python CAD kernel (OpenCascade-based)
- **OCP CAD Viewer** — VS Code extension for 3D visualization
- **trimesh + manifold3d** — STL comparison and boolean operations
- **numpy-stl** — Mesh property calculations + STL assembly

---

## License

This project reconstructs parts from the [Thor robot arm](https://github.com/AngelLM/Thor) by AngelLM, which is shared under open-source terms. This reconstruction is for educational purposes.









                                    =======================Thor-Base-Assembly===================

This project focuses on reverse engineering 3D geometry from STL files to recreate accurate parametric models. The process begins by converting the STL mesh into a solid body in Autodesk Fusion 360, enabling access to parametric features. Key coordinates and dimensions of various sketch profiles and features—such as extrudes, cuts, and revolves—are then measured to replicate the original design. These feature details are fed into Antigravity, and with the assistance of Claude, a build123d script is generated. Running this script produces a reconstructed 3D model that closely matches the original geometry. To validate accuracy, the volume of the generated model is compared with the original using Fusion 360; the volumetric differences observed are 0.002 for Part 1, 0 for Parts 2 and 3, and 0.001 for Part 4, 0.005 for Part 5 . The repository is organized into five part files, each containing four folders that include the original STL file, the generated output model, volumetric comparison results, and the corresponding code used for reconstruction.}





             ===========================# Assem-Art3 Parametric Models ==============================

This folder contains build123d reconstructions of mechanical parts
reverse-engineered from original STEP files. Each script is self-contained,
builds the CAD solid from named parameters, exports STEP + STL, and validates
the output against a reference mesh when available.

All scripts export to:

```text
/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d
```

## Requirements

Install the CAD/export dependencies:

```bash
python3 -m pip install --user build123d cadquery trimesh manifold3d scipy ocp-vscode
```

`cadquery` is used for watertight STL export via STEP round-trip. `trimesh`,
`manifold3d`, and `scipy` are used for inline STL validation. `ocp-vscode` is
optional and enables the OCP CAD Viewer inside VS Code.

If Python tries to write bytecode into a protected cache folder, run any script
with:

```bash
PYTHONPYCACHEPREFIX=/tmp/codex_pycache python3 <script>.py
```

---
---

# 1. Art3Pulley Parametric Model

The parametric version is:

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

## Run

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art3Pulley_parametric_pure.py
```

## Outputs

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

The script calculates symmetric difference at CAD level first, using the
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

The pure-parametric script repairs the generated STL after export with a small
mesh cleanup only. If either mesh is still not watertight or not a valid volume,
the script reports:

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

---
---

# 2. Art3Body Parametric Model

The main script is:

```text
Art3Body_main_dome_parametric.py
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

The supplied `Art3Body.stl` is about 10× smaller than the build123d model in
linear units. The script prints raw values first, then auto-scales the reference
mesh for comparison using the bounding-box diagonal. This does not modify the
reference file.

The approximate symmetric-difference volume proxy is computed as:

```text
0.5 * (generated_area * mean_distance_to_reference
     + reference_area * mean_distance_to_generated)
```

The exact boolean symmetric difference is attempted after that. It runs
because the generated STL is watertight.

## Current Validation

Latest run:

```text
Generated watertight : True
Reference watertight : True
Generated faces      : 34,244
Reference faces      : 34,354

Generated bbox extents : 1101.0 × 1100.7 × 1525.0 mm
Reference auto-scale   : 9.9997×

Scaled volume delta    : −0.642%
Boolean sym-diff vol   : 5,130,795.726 mm³
```

## Notes

- All dimensions in the parametric model are in millimeters at `SCALE = 1.0`.
- The validation auto-scale is only for comparing against `Art3Body.stl`, whose
  linear units are approximately 10× smaller.

---
---

# 3. Art4MotorGear — Reconstruction Approaches

## Overview

This section compares two independent approaches for reconstructing the
**Art4MotorGear** helical spur gear from the original STEP/STL reference
geometry. Both scripts produce a full-size (×10 scaled) build123d solid with
integral shaft section, keyway, central bore, and counterbored horizontal bore.

**Reference part specifications:**

```text
Teeth              : 10
Module (transverse): 18 mm
Pressure angle     : 20°
Helix angle        : 29.5341°
Face width         : 130.0184 mm
Pitch diameter     : 180 mm (r = 90)
Tip diameter       : 216 mm (r = 108)
Root diameter      : 135 mm (r = 67.5)
Shaft radius       : 120 mm, depth 100 mm
Central bore       : r = 25 mm (through)
Overall Z span     : −100 → +130 mm (230 mm)
Ref STL volume (×10): 6,935,349.84 mm³
```

## Approach 1 — DXF Slicing + Polar Loft

**Script:** `Art4MotorGear_slicing.py`

### How It Works

1. Reads axis-Z DXF cross-sections produced by the STEP slicer from
   `slicing-1/axis_Z/`. These DXF files contain the outer loop of the gear at
   each Z height, at 0.1× scale.
2. Loads the topmost slice and converts it to a polar-resampled radial profile
   (880 samples around 360°). This captures the exact tooth shape from the
   reference geometry including root fillets, tip geometry, and any non-standard
   tooth modifications.
3. Generates 54 Z-sections by shifting the polar profile according to the
   helical twist formula (`twist_per_mm × ΔZ`) and applying a small radial
   offset correction (`PROFILE_RADIAL_OFFSET = −0.051 mm`).
4. Each section is built as a `Polyline` sketch and all sections are connected
   via `loft(ruled=True)`.
5. Shaft, bore, keyway, and counterbored horizontal bore are added as standard
   build123d CSG operations.

### Strengths

- Highest geometric fidelity — tooth profile comes directly from the reference
  STEP geometry.
- Best volumetric match: +0.0015% volume difference vs reference STL.
- Best symmetric difference: 0.71% sym-diff/union.

### Limitations

- Requires DXF slice files from the slicer pipeline as input — not standalone.
- Requires `ezdxf` as an additional dependency.
- Very large output files: 46,655 B-Rep faces.
- Visible staircase artifacts on tooth flanks from `loft(ruled=True)`.
- Longer computation time due to high polygon count.

## Approach 2 — Pure Parametric Involute + MakePipeShell

**Script:** `Art4MotorGear_parametric.py`

### How It Works

1. Generates the gear tooth cross-section from first principles using involute
   curve mathematics: each tooth consists of left and right involute flanks
   (computed from `base_r`, `pressure_angle`), circular tip arcs, radial
   transitions to the root circle, and root arcs between teeth. The profile is
   a closed 660-point polyline.
2. Builds a straight spine wire along Z (0 → face_width) and an auxiliary helix
   polyline at the pitch radius. The helix defines the twist direction and rate.
3. Uses OCC's `BRepOffsetAPI_MakePipeShell` with the auxiliary helix to sweep
   the tooth profile along the spine with continuous helical twist. This
   produces smooth ruled surfaces — not stacked polygons.
4. Shaft, bore, keyway, and counterbored horizontal bore are added identically
   to Approach 1.

### Strengths

- Completely standalone — no DXF files, no slicer pipeline, no external
  geometry inputs.
- Smooth helical tooth flanks via `MakePipeShell` sweep with no staircase
  artifacts.
- Dramatically smaller output: 675 faces vs 46,655 (roughly 70× fewer).
- Fully parametric — changing any gear parameter regenerates the entire
  geometry.
- Minimal dependencies: only `build123d` (and its OCC backend) required.

### Limitations

- Lower geometric fidelity in tooth detail — the involute profile is
  mathematically ideal, no root fillets or tip rounding.
- Slightly higher volumetric difference: +0.17% vs CAD target, +0.84% vs
  reference STL.
- Higher symmetric difference: 1.31% sym-diff/union vs 0.71%.

## Head-to-Head Comparison

```text
Metric                    DXF Slicing       Parametric        Winner
─────────────────────────────────────────────────────────────────────
Volume vs ref STL         +0.0015%          +0.84%            DXF Slicing
Sym-diff / union          0.71%             1.31%             DXF Slicing
B-Rep faces               46,655            675               Parametric (70×)
STEP file size            tens of MB        ~4 MB             Parametric
STL file size             large             ~794 KB           Parametric
Surface quality           staircase         smooth helical    Parametric
Dependencies              ezdxf + DXF       build123d only    Parametric
Standalone                no                yes               Parametric
Parametric flexibility    limited           full              Parametric
Root fillet accuracy      captured          missing           DXF Slicing
Computation time          slower            faster            Parametric
STL watertight            yes               yes               Tie
Winding consistent        yes               yes               Tie
Boundary edges            0                 0                 Tie
Non-manifold edges        0                 0                 Tie
```

## Detailed Output — DXF Slicing (Approach 1)

```text
Sections  :   54   samples/section: 880
Volume    :       6936952.3040 mm³
Faces     : 46655
X span    : -120.0 -> 120.0  (240.0 mm)
Y span    : -120.0 -> 120.0  (240.0 mm)
Z span    : -100.0 -> 130.0  (230.0 mm)

STL Reference Comparison
Ref volume      :         6935349.84 mm³
Gen volume      :         6935454.39 mm³
Volume diff %   :       +0.00150750 %
Sym-diff volume :       49119.477789 mm³
Sym-diff union %:        0.70574349 %

STL Health
Watertight       : True
Winding          : True
Boundary edges   : 0
Nonmanifold edges: 0
```

## Detailed Output — Parametric (Approach 2)

```text
Tooth profile  : 660 points, 24456 mm²
Helix twist    : 46.90° over 130.0 mm
Gear body      : 3179719 mm³, 662 faces

Volume    :       6999800.0424 mm³
Target    :            6988013 mm³
Delta     :           +0.1687 %
Faces     :  675

STL Reference Comparison
Ref volume      :         6935349.84 mm³
Gen volume      :         6993612.77 mm³
Volume diff %   :       +0.84008647 %
Sym-diff vol    :       91788.944657 mm³
Sym-diff/union  :        1.30932988 %

STL Health
Watertight       : True
Winding          : True
Boundary edges   : 0
Nonmanifold edges: 0
STEP size  : 3952 KB
STL  size  : 794 KB
```

## When To Use Which

**Use the DXF Slicing approach when:**
- Maximum geometric accuracy is the priority and slicer output is available.
- The part has non-standard tooth modifications not captured by involute math.
- Downstream workflow can handle large STEP/STL files.
- Visual staircase artifacts are acceptable.

**Use the Parametric approach when:**
- A standalone, self-contained script is needed.
- Clean, smooth B-Rep output is required for downstream CAD, rendering, or
  3D printing.
- Small file sizes matter.
- The gear follows standard involute geometry and ~1% sym-diff is acceptable.
- Rapid iteration on gear parameters is needed.

## Dependencies

DXF Slicing (Approach 1):

```text
build123d
ezdxf (for reading DXF slice files)
cadquery (optional, watertight STL export)
trimesh, manifold3d, numpy (optional, STL validation)
DXF slice files from slicer pipeline (slicing-1/axis_Z/)
```

Parametric (Approach 2):

```text
build123d (includes OCC backend for MakePipeShell)
cadquery (optional, watertight STL export)
trimesh, manifold3d, numpy (optional, STL validation)
ocp-vscode (optional, interactive 3D viewing)
```

---
---

# 4. Art4BearingRing Parametric Model

The parametric version is:

```text
Art4BearingRing_parametric.py
```

It generates:

```text
Art4BearingRing_parametric.step
Art4BearingRing_parametric.stl
```

## Purpose

`Art4BearingRing_parametric.py` builds a large bearing ring directly from named
parameters. The script does not import DXF or STEP files at runtime. All
dimensions are baked into the script as editable parametric data.

## Run

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art4BearingRing_parametric.py
```

## Outputs

Generated files:

```text
Art4BearingRing_parametric.step
Art4BearingRing_parametric.stl
```

The script also compares the generated model against:

```text
Art4BearingRing.stl
```

when that reference file is present.

## Main Parameters

All dimensions are in millimeters.

Stepped disc body:

```python
lower_radius    = 400.0     # Lower disc outer radius
lower_height    =  40.0     # Lower disc height (z = 0 → 40)
upper_radius    = 500.0     # Upper disc outer radius
upper_height    =  60.0     # Upper disc height (z = 40 → 100)
total_height    = 100.0     # Overall height
```

Central bore and torus groove:

```python
bore_radius     = 360.0     # Central through-bore radius
torus_R         = 350.0     # Torus major radius (groove centre from Z-axis)
torus_r         =  32.0     # Torus minor radius (groove cross-section)
torus_z         =  50.0     # Torus centre height
```

Counterbored mounting holes:

```python
hole_positions  = [(390, 225), (390, -225), (-390, 225), (-390, -225)]
thru_bore_r     =  17.0     # Through-bore radius (z = 40 → 75)
thru_bore_depth =  35.0     # Through-bore depth
cbore_r         =  33.5     # Counterbore radius (z = 75 → 100)
cbore_depth     =  25.0     # Counterbore depth
```

Side lubrication bore:

```python
side_bore_r     =  37.0     # Bore + cone junction radius
side_bore_z     =  50.0     # Bore axis height
side_cyl_x_end  = -405.0    # Cylinder end X
cone_x_end      = -360.0    # Cone narrows to here
cone_angle_deg  =   7.9696  # Cone semi-angle (degrees)
```

## Methodology

The model was reconstructed as a build123d parametric script. The final script
creates the CAD body from primitive solids and named dimensions.

The workflow used was:

1. Build the stepped disc body from two concentric cylinders:

```text
lower disc (r=400, z=0..40) + upper disc (r=500, z=40..100)
```

2. Subtract major features:

```text
central through bore (r=360, full height)
toroidal ball-race groove (R=350, r=32, at z=50)
4× counterbored mounting holes at (±390, ±225)
horizontal side bore + conical entry (revolve profile)
```

3. The side lubrication bore is built as a single revolve of a closed profile
   (cylinder rectangle + cone trapezoid) around the bore axis. The profile is
   defined in a custom plane at bore height, and the revolve subtracts the
   bore and cone in one operation.

4. Export the generated CAD model as STEP.

5. Export the generated STEP as STL through CadQuery for watertight mesh.

6. Compare the generated model against the reference STL file using volume
   difference and symmetric boolean difference.

## Current Validation

Geometry verified against original STEP file:

```text
Volume error  : < 0.001%
Bounding box  : 1000 × 1000 × 100 mm
```

## Volume Difference

The CAD volume is taken directly from the build123d solid:

```python
_step_vol = result.volume
```

The percentage difference against the reference STL is:

```text
Volume diff (%) = (generated volume − reference volume)
                  / reference volume × 100
```

Positive = more material than reference, negative = less material.

## STL Symmetric Difference

STL symmetric difference is calculated using boolean operations on meshes:

```python
_diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
_diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
_union   = trimesh.boolean.union([_gen, _ref], engine="manifold")
_sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100
```

Meshes are repaired (normals, winding, holes) before boolean operations. If
booleans fail, volume-only comparison is reported.

## STL Scaling Check

The reference STL may not be in the same unit scale, so the script compares
bounding-box spans and estimates a scale factor:

```python
_scale = median(gen_spans / ref_spans)
_scale = round(_scale * 2) / 2
```

If the scale differs from `1.0`, the reference mesh is scaled before validation.

## Notes

- The revolve-based side bore construction avoids fragile multi-step boolean
  chains and produces a clean single subtraction.
- The toroidal groove is placed at part mid-height (z=50), matching the
  ball-race groove position in the original STEP.

---
---

# 5. Art4MotorFix Parametric Model

The parametric version is:

```text
Art4MotorFix_parametric.py
```

It generates:

```text
Art4MotorFix_parametric.step
Art4MotorFix_parametric.stl
```

## Purpose

`Art4MotorFix_parametric.py` builds a motor fixing plate directly from named
parameters. The script does not import DXF or STEP files at runtime. All
dimensions are baked into the script as editable parametric data.

## Run

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art4MotorFix_parametric.py
```

## Outputs

Generated files:

```text
Art4MotorFix_parametric.step
Art4MotorFix_parametric.stl
```

The script also compares the generated model against:

```text
Art4MotorFix.stl
```

when that reference file is present.

## Main Parameters

All dimensions are in millimeters.

Base plate:

```python
plate_length    = 423.0     # X extent of base plate
plate_width     = 403.0     # Y extent of base plate
plate_height    =  30.0     # Z height of base plate (z = 0 → 30)
chamfer_leg     =  50.0     # 45° corner chamfer leg length
```

Base plate features:

```python
central_bore_r  = 120.0     # Central bore radius (full plate height)
corner_hole_r   =  17.0     # Corner bore radius
corner_hole_pos = [(-155, -155), (-155, 155), (155, -155), (155, 155)]
```

Mounting block (left side):

```python
block_x1        = -211.5    # Block left face X
block_x2        = -161.5    # Block right face X
block_y_half    = 100.0     # Block half-width in Y (Y = −100 → +100)
block_z_top     =  80.0     # Block top Z
```

Horizontal blind bores in block:

```python
hbore_r         =  17.0     # Bore radius
hbore_depth     =  10.0     # Depth from each face (blind bore)
hbore_z         =  50.0     # Bore axis height
hbore_y_pos     = [45.0, -45.0]
```

V-groove slot channels:

```python
slot_x1         = -201.5    # Slot inner X
slot_x2         = -171.5    # Slot outer X
slot_y_half     =  29.012   # Half-width of slot in Y
slot_bot_z      =  33.25    # Slot flat-bottom Z
slot_edge_z     =  16.5     # Slot inclined floor Z at Y-edges (V-groove apex)
```

## Methodology

The model was reconstructed as a build123d parametric script. The final script
creates the CAD body from primitive solids, sketch-based extrudes, and named
dimensions.

The workflow used was:

1. Build the base plate as a rectangular box:

```text
423 × 403 × 30 mm base plate
```

2. Add the left-side mounting block:

```text
50 × 200 × 50 mm block (z = 30 → 80)
```

3. Subtract corner chamfers as triangular prism extrudes:

```text
4× 45° corner chamfers (50 mm leg, sketch + extrude through plate height)
```

4. Subtract plate features:

```text
central bore r=120 (full plate height)
4× corner bores r=17 at (±155, ±155)
```

5. Subtract block features:

```text
4× horizontal blind bores r=17 (10 mm from each X face, at Y=±45, Z=50)
2× V-groove slot channels (rectangular upper + triangular inclined floor)
```

6. The V-groove slot channels are each built as two subtractions: a rectangular
   box for the upper zone (z = slot_bot_z → block_z_top) and a triangular
   prism sketch extruded on the YZ plane for the inclined V-floor (z =
   slot_edge_z → slot_bot_z). The triangle is defined with base at slot_bot_z
   and apex pointing down to slot_edge_z.

7. Export the generated CAD model as STEP.

8. Export the generated STEP as STL through CadQuery for watertight mesh.

9. Compare the generated model against the reference STL file.

## Current Validation

Geometry verified against original STEP file:

```text
Volume error  : < 0.001%
Bounding box  : 423 × 403 × 80 mm
```

## Volume Difference

```text
Volume diff (%) = (generated volume − reference volume)
                  / reference volume × 100
```

## STL Symmetric Difference

```python
_diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
_diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
_union   = trimesh.boolean.union([_gen, _ref], engine="manifold")
_sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100
```

The script includes a `_make_watertight()` repair function as fallback: if
either mesh is not watertight, it fills holes and fixes normals. As a last
resort, it voxelizes and reconverts to a box mesh for boolean operations.

## STL Scaling Check

```python
_scale = median(gen_spans / ref_spans)
_scale = round(_scale * 2) / 2
```

## Notes

- The 45° corner chamfers are built as sketch-based triangular extrudes rather
  than using the build123d `chamfer()` API, because the chamfer must span full
  plate height and only apply to the four plate corners.
- Horizontal blind bores use a rotated cylinder (90° around Y) with
  `Align.MAX` / `Align.MIN` to drill inward from each block face.

---
---

# 6. Art23Optodisk Parametric Model

The parametric version is:

```text
Art23Optodisk_parametric.py
```

It generates:

```text
Art23Optodisk_parametric.step
Art23Optodisk_parametric.stl
```

## Purpose

`Art23Optodisk_parametric.py` builds an optodisk / encoder disc housing directly
from named parameters. The script does not import DXF or STEP files at runtime.
All dimensions are baked into the script as editable parametric data.

## Run

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/Art23Optodisk_parametric.py
```

## Outputs

Generated files:

```text
Art23Optodisk_parametric.step
Art23Optodisk_parametric.stl
```

The script also compares the generated model against:

```text
Art23Optodisk.stl
```

when that reference file is present.

## Main Parameters

All dimensions are in millimeters.

Main arc ring:

```python
ring_r_inner    = 282.0     # Ring inner radius
ring_r_outer    = 292.0     # Ring outer radius
ring_height     = 150.0     # Ring total height (z = 0 → 150)
front_cut_y     = -30.0     # Y position of flat front face
```

Side arm sectors:

```python
arm_r_inner     = 210.0     # Arm inner wall radius
arm_y_max       =  70.0     # Arm extends from Y = 0 → 70
arm_height      =  50.0     # Arm height (z = 0 → 50)
```

Top slot:

```python
slot_half_width =   5.0     # Slot half-width (X = −5 → +5)
slot_z_start    =  50.0     # Slot floor height (z = 50 → 150)
```

Counterbored fixing holes:

```python
hole_positions  = [(250.0, 35.0), (-250.0, 35.0)]
thru_bore_r     =  17.0     # Through-bore radius (z = 0 → 20)
thru_bore_depth =  20.0     # Through-bore depth
cbore_r         =  29.5     # Counterbore radius (z = 20 → 50)
cbore_depth     =  30.0     # Counterbore depth
```

## Methodology

The model was reconstructed as a build123d parametric script. The final script
creates the CAD body from primitive solids, box-clip boolean chains, and named
dimensions.

The workflow used was:

1. Build the main arc ring as an annulus:

```text
full outer cylinder (r=292, h=150)
− inner cylinder (r=282, h=150)
− flat front cut box (everything below Y=−30)
```

2. Build two symmetric arm sectors as independent BuildPart solids:

```text
annular sector (r=210..282, h=50)
clipped to correct X half (left or right)
clipped to Y = 0 → 70
```

   Each arm is built inside its own `BuildPart()` context and then `add()`-ed
   to the main part. This avoids accidentally clipping the ring body during
   the arm box subtractions.

3. Subtract the top slot:

```text
box (10 mm wide, ring wall thickness, z = 50 → 150) at ring apex
```

4. Subtract counterbored fixing holes:

```text
2× through bore (r=17, z = 0 → 20)
2× counterbore (r=29.5, z = 20 → 50)
```

5. Export the generated CAD model as STEP.

6. Export the generated STEP as STL through CadQuery for watertight mesh.

7. Compare the generated model against the reference STL file.

## Current Validation

Geometry verified against original STEP file:

```text
Volume error  : < 0.001%
Face count    : 24 (exact match)
Bounding box  : 584 × 322 × 150 mm
```

## Volume Difference

```text
Volume diff (%) = (generated volume − reference volume)
                  / reference volume × 100
```

## STL Symmetric Difference

```python
_diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
_diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
_union   = trimesh.boolean.union([_gen, _ref], engine="manifold")
_sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100
```

## STL Scaling Check

```python
_scale = median(gen_spans / ref_spans)
_scale = round(_scale * 2) / 2
```

## Notes

- The arm sectors are built as separate `BuildPart()` solids to isolate their
  clip-box subtractions from the main ring body. Using box clipping inside the
  main context would incorrectly cut into the ring.
- The front cut uses a large oversized box shifted to Y = front_cut_y − half_size
  to cleanly remove the arc segment below Y = −30.

---
---

# 7. CommonBearingFixThrough Parametric Model

The parametric version is:

```text
CommonBearingFixThrough_parametric.py
```

It generates:

```text
CommonBearingFixThrough_parametric.step
CommonBearingFixThrough_parametric.stl
```

## Purpose

`CommonBearingFixThrough_parametric.py` builds a bearing-mounting plate directly
from named parameters. The script does not import DXF or STEP files at runtime.
All dimensions are baked into the script as editable parametric data.

## Run

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/CommonBearingFixThrough_parametric.py
```

## Outputs

Generated files:

```text
CommonBearingFixThrough_parametric.step
CommonBearingFixThrough_parametric.stl
```

The script also compares the generated model against:

```text
CommonBearingFixThrough.stl
```

when that reference file is present.

## Main Parameters

All dimensions are in millimeters.

Central hub:

```python
hub_radius_outer    = 79.0      # Outer radius of the central hub cylinder
hub_bore_radius     = 50.0      # Central through-bore radius
```

Arms:

```python
arm_length          = 300.0     # Full arm span in X (−150 → +150)
arm_width           =  65.0     # Arm width in Y (= 2 × 32.5 mm)
```

Counterbored fixing holes:

```python
hole_cx             = 110.0     # Hole-centre X offset from origin
counterbore_radius  =  29.5     # Large bore radius (counterbore)
counterbore_depth   =  30.0     # Counterbore depth from top surface
thru_bore_radius    =  17.0     # Small through-bore radius (full height)
```

Overall:

```python
total_height        =  40.0     # Part height (Z)
```

## Methodology

The model was reconstructed as a build123d parametric script. The final script
creates the CAD body from primitive solids and named dimensions.

The workflow used was:

1. Build the solid body from two primitives:

```text
central hub cylinder (r=79, h=40)
+ rectangular arm block (300 × 65 × 40)
```

   The cylinder and box are unioned automatically by build123d since both are
   added in the same BuildPart context.

2. Subtract features:

```text
central through bore (r=50, full height)
2× through bore (r=17, full height, at X=±110)
2× counterbore (r=29.5, 30 mm deep from top surface, at X=±110)
```

3. Export the generated CAD model as STEP.

4. Export the generated CAD as STL via build123d.

5. Compare the generated model against the reference STL file.

## Current Validation

Geometry verified against original STEP file:

```text
Volume error  : < 0.001%
Face count    : 17 (exact match)
Bounding box  : 300 × 158 × 40 mm
```

## Volume Difference

```text
Volume diff (%) = (generated volume − reference volume)
                  / reference volume × 100
```

## STL Symmetric Difference

```python
_diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
_diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
_union   = trimesh.boolean.union([_gen, _ref], engine="manifold")
_sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100
```

## STL Scaling Check

```python
_scale = median(gen_spans / ref_spans)
_scale = round(_scale * 2) / 2
```

## Notes

- This is the simplest part in the collection — two additive primitives and
  five subtractive cylinders. No sketch-based operations are needed.
- STL export uses build123d directly (not the CadQuery round-trip) since the
  geometry is simple enough to produce watertight meshes.

---
---

# 8. CommonBearingFixThrough_parametric001 (Rotated Variant)

The parametric version is:

```text
CommonBearingFixThrough_parametric001.py
```

It generates:

```text
CommonBearingFixThrough_parametric.step
CommonBearingFixThrough_parametric.stl
```

(Same output filenames as the base variant — they share the output path.)

## Purpose

`CommonBearingFixThrough_parametric001.py` builds the same bearing-mounting
plate as `CommonBearingFixThrough_parametric.py`, but applies a 90° rotation
around the Y-axis after build. This reorientation is needed for alternate
assembly positioning.

## Run

```bash
python3 /Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d/CommonBearingFixThrough_parametric001.py
```

## Outputs

Generated files:

```text
CommonBearingFixThrough_parametric.step
CommonBearingFixThrough_parametric.stl
```

The script also compares the generated model against:

```text
CommonBearingFixThrough.stl
```

when that reference file is present.

## Main Parameters

All parameters are identical to `CommonBearingFixThrough_parametric.py`. See
section 7 above.

## Methodology

The workflow is identical to the base variant (section 7), with one addition:

After building the solid, a 90° Y-axis rotation is applied:

```python
result = part.part.rotate(Axis.Y, 90)
```

This swaps the X and Z axes of the part. The original bounding box
(300 × 158 × 40) becomes (40 × 65 × 300) after rotation.

All export and validation steps proceed on the rotated result.

## Current Validation

```text
Volume error  : < 0.001%
Face count    : 17 (exact match)
Bounding box  : 40 × 65 × 300 mm (post-rotation)
```

## Notes

- This variant exists specifically for assembly orientation. The geometry is
  byte-for-byte identical to the base variant before rotation.
- Both variants write to the same output filenames. Run only one at a time, or
  rename the output paths if both orientations are needed simultaneously.

---
---

# Common Validation Reference

This section documents the validation metrics used across all scripts.

## Volume Difference

The CAD volume is taken directly from the build123d solid:

```python
_step_vol = result.volume
```

The percentage difference against the reference is:

```text
Volume diff (%) = (generated volume − reference volume)
                  / reference volume × 100
```

So:

```text
positive value = generated model has more material than reference
negative value = generated model has less material than reference
```

Target: < 1%.

## STL Symmetric Difference

STL symmetric difference measures how much material differs spatially between
the generated STL and the reference STL. It requires both triangle meshes to be
valid boolean volumes.

It is calculated using boolean operations on meshes:

```python
_diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
_diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
_union   = trimesh.boolean.union([_gen, _ref], engine="manifold")
_sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100
```

Meaning:

```text
generated − reference = material present only in generated model
reference − generated = material missing from generated model
union                 = total occupied volume of both models combined
```

The final metric is:

```text
Symmetric difference (%) =
    (extra generated volume + missing generated volume)
    / union volume × 100
```

Target: < 2%. A lower value means the generated model is closer to the
reference. If either mesh is not watertight, the script reports:

```text
Sym-diff : [skipped — mesh is not a valid boolean volume]
```

That does not mean the CAD model failed. It means the STL tessellation is not
suitable for mesh booleans. In that case, use volume difference only.

## CAD Symmetric Difference

Some scripts (Art3Pulley, Art3Body) also calculate symmetric difference at CAD
level using the generated solid and the reference STEP solid directly. This
avoids false failures from non-watertight STL tessellation:

```python
_cad_gen_only = result.cut(_ref_cad).volume
_cad_ref_only = _ref_cad.cut(result).volume
_cad_union_est = (
    (result.volume + _cad_ref_only)
    + (_ref_cad.volume + _cad_gen_only)
) / 2.0
_cad_sym_pct = (_cad_gen_only + _cad_ref_only) / _cad_union_est * 100
```

CAD symmetric difference is the primary comparison metric when available.

## STL Scaling Check

The reference STL may not be in the same unit scale as the generated model, so
scripts compare bounding-box spans and estimate a scale factor:

```python
_spans_g = _gen.bounds[1] - _gen.bounds[0]
_spans_r = _ref_raw.bounds[1] - _ref_raw.bounds[0]
_scale = median(_spans_g / _spans_r)
_scale = round(_scale * 2) / 2      # or round(_scale * 4) / 4
```

If the scale differs noticeably from `1.0`, the reference mesh copy is scaled
before validation.

## STL Export Strategy

Some scripts export STL via a STEP → CadQuery round-trip:

```python
import cadquery as cq
_cq_shape = cq.importers.importStep(_step_path)
cq.exporters.export(_cq_shape, _stl_path, exportType="STL",
                     tolerance=0.01, angularTolerance=0.1)
```

This produces more reliable watertight meshes than direct `export_stl()` from
build123d on complex geometry (torus grooves, revolve profiles, etc.). Simpler
parts use `export_stl()` directly.

## Viewer

Scripts attempt to display the result in the OCP CAD Viewer (VS Code
extension). If unavailable, they fall back to opening the exported STEP or STL
with the system default viewer (`open` on macOS, `xdg-open` on Linux).

### Known Environment Issues

- **ocp_vscode port file errors** — Fix: clear stale port files from `/tmp`
  and `/var/folders`.
- **macOS failing to open .step files** — Fallback: scripts open the STL file
  instead, or open the file manually.






