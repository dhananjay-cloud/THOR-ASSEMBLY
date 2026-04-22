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
