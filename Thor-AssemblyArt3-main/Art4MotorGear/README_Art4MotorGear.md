# Art4MotorGear — Reconstruction Approaches

## Overview

This document compares two independent approaches for reconstructing the **Art4MotorGear** helical spur gear from the original STEP/STL reference geometry. Both scripts produce a full-size (×10 scaled) build123d solid with integral shaft section, keyway, central bore, and counterbored horizontal bore.

**Reference part specifications:**

| Property | Value |
|---|---|
| Teeth | 10 |
| Module (transverse) | 18 mm |
| Pressure angle | 20° |
| Helix angle | 29.5341° |
| Face width | 130.0184 mm |
| Pitch diameter | 180 mm (r = 90) |
| Tip diameter | 216 mm (r = 108) |
| Root diameter | 135 mm (r = 67.5) |
| Shaft radius | 120 mm, depth 100 mm |
| Central bore | r = 25 mm (through) |
| Overall Z span | −100 → +130 mm (230 mm) |
| Reference STL volume (×10) | 6,935,349.84 mm³ |

---

## Approach 1 — DXF Slicing + Polar Loft

**Script:** `Art4MotorGear_slicing.py`

### How It Works

1. Reads axis-Z DXF cross-sections produced by the STEP slicer from `slicing-1/axis_Z/`. These DXF files contain the OUTER loop of the gear at each Z height, at 0.1× scale.
2. Loads the topmost slice and converts it to a polar-resampled radial profile (880 samples around 360°). This captures the exact tooth shape from the reference geometry including root fillets, tip geometry, and any non-standard tooth modifications.
3. Generates 54 Z-sections by shifting the polar profile according to the helical twist formula (`twist_per_mm × ΔZ`) and applying a small radial offset correction (`PROFILE_RADIAL_OFFSET = −0.051 mm`).
4. Each section is built as a `Polyline` sketch and all sections are connected via `loft(ruled=True)`.
5. Shaft, bore, keyway, and counterbored horizontal bore are added as standard build123d CSG operations.

### Strengths

- **Highest geometric fidelity**: The tooth profile comes directly from the reference STEP geometry, so it captures the exact involute shape, root fillets, tip rounding, and any non-standard modifications present in the original CAD model.
- **Best volumetric match**: +0.0015% volume difference vs reference STL — essentially zero.
- **Best symmetric difference**: 0.71% sym-diff/union — the tightest shape match achievable without the original B-Rep.

### Limitations

- **Requires DXF slice files** from the slicer pipeline as input — not standalone.
- **Requires `ezdxf`** as an additional dependency.
- **Very large output files**: The ruled loft through 54 sections of 880-point polylines generates 46,655 B-Rep faces, resulting in large STEP and STL files.
- **Visible staircase artifacts** on tooth flanks when viewed closely, because `loft(ruled=True)` creates flat planar facets between adjacent Z-sections rather than smooth helical surfaces.
- **Longer computation time** due to the high polygon count in both the loft operation and the subsequent boolean CSG operations on the resulting high-face-count solid.

---

## Approach 2 — Pure Parametric Involute + MakePipeShell

**Script:** `Art4MotorGear_parametric.py`

### How It Works

1. Generates the gear tooth cross-section from first principles using involute curve mathematics: each tooth consists of left and right involute flanks (computed from `base_r`, `pressure_angle`), circular tip arcs, radial transitions to the root circle, and root arcs between teeth. The profile is a closed 660-point polyline.
2. Builds a straight spine wire along Z (0 → face_width) and an auxiliary helix polyline at the pitch radius. The helix defines the twist direction and rate.
3. Uses OCC's `BRepOffsetAPI_MakePipeShell` with the auxiliary helix to sweep the tooth profile along the spine with continuous helical twist. This produces smooth ruled surfaces — not stacked polygons.
4. Shaft, bore, keyway, and counterbored horizontal bore are added identically to Approach 1.

### Strengths

- **Completely standalone**: No DXF files, no slicer pipeline, no external geometry inputs. All tooth geometry is derived from five parameters: `num_teeth`, `trans_module`, `pressure_angle`, `helix_angle`, `face_width`.
- **Smooth helical tooth flanks**: The `MakePipeShell` sweep produces clean B-Rep surfaces with no staircase artifacts. The gear looks correct at any zoom level.
- **Dramatically smaller output files**: 675 faces vs 46,655 — roughly 70× fewer. STEP file is ~4 MB instead of tens of MB.
- **Faster computation**: Fewer faces means faster boolean operations and faster STL export.
- **Fully parametric**: Changing any gear parameter (module, teeth count, helix angle, etc.) regenerates the entire geometry. No need to re-slice anything.
- **Minimal dependencies**: Only `build123d` (and its OCC backend) required. `cadquery` and `trimesh` are optional for STL export and validation.

### Limitations

- **Lower geometric fidelity in tooth detail**: The involute profile is mathematically ideal — it does not include root fillets (the original has tori at each tooth root), tip rounding, or any non-standard tooth modifications present in the original CAD model.
- **Slightly higher volumetric difference**: +0.17% vs CAD target, +0.84% vs reference STL — still excellent but measurably larger than Approach 1.
- **Higher symmetric difference**: 1.31% sym-diff/union vs 0.71% — the shape deviation is roughly double, primarily concentrated at the tooth root fillet region and minor tip geometry differences.

---

## Head-to-Head Comparison

| Metric | DXF Slicing (Approach 1) | Parametric (Approach 2) | Winner |
|---|---|---|---|
| **Volume vs reference STL** | +0.0015% | +0.84% | DXF Slicing |
| **Sym-diff / union** | 0.71% | 1.31% | DXF Slicing |
| **B-Rep faces** | 46,655 | 675 | Parametric (70× fewer) |
| **STEP file size** | Large (tens of MB) | ~4 MB | Parametric |
| **STL file size** | Large | ~794 KB | Parametric |
| **Surface quality** | Staircase artifacts on flanks | Smooth helical surfaces | Parametric |
| **Dependencies** | ezdxf + DXF slice files | build123d only | Parametric |
| **Standalone** | No (needs slicer output) | Yes | Parametric |
| **Parametric flexibility** | Limited (tied to sliced geometry) | Full (change any parameter) | Parametric |
| **Root fillet accuracy** | Captured from reference | Missing (flat root arcs) | DXF Slicing |
| **Computation time** | Slower (high poly loft + booleans) | Faster | Parametric |
| **STL watertight** | Yes | Yes | Tie |
| **STL winding consistent** | Yes | Yes | Tie |
| **Boundary edges** | 0 | 0 | Tie |
| **Non-manifold edges** | 0 | 0 | Tie |

---

## Detailed Output Comparison

### DXF Slicing (Approach 1)

```
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

### Parametric (Approach 2)

```
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

---

## When to Use Which

**Use the DXF Slicing approach when:**
- Maximum geometric accuracy is the priority and the slicer pipeline output is available.
- The part has non-standard tooth modifications that cannot be captured by standard involute math.
- The downstream workflow can handle large STEP/STL files.
- Visual staircase artifacts on tooth flanks are acceptable (or the output will be used for volume comparison rather than visual rendering).

**Use the Parametric approach when:**
- A standalone, self-contained script is needed with no external geometry dependencies.
- Clean, smooth B-Rep output is required for downstream CAD operations, rendering, or 3D printing.
- Small file sizes matter (version control, sharing, cloud storage).
- The gear follows standard involute geometry and the ~1% symmetric difference is acceptable.
- Rapid iteration on gear parameters is needed (changing module, tooth count, helix angle, etc.).

---

## Dependencies

### DXF Slicing (Approach 1)
- `build123d`
- `ezdxf` (for reading DXF slice files)
- `cadquery` (optional, for high-quality STL export)
- `trimesh`, `manifold3d`, `numpy` (optional, for STL validation and reference comparison)
- DXF slice files from the slicer pipeline (`slicing-1/axis_Z/`)

### Parametric (Approach 2)
- `build123d` (includes OCC backend for MakePipeShell)
- `cadquery` (optional, for high-quality STL export)
- `trimesh`, `manifold3d`, `numpy` (optional, for STL validation and reference comparison)
- `ocp-vscode` (optional, for interactive 3D viewing)
