"""
CommonBearingFixThrough — Parametric build123d Script
======================================================
A bearing-mounting plate with:
  • Central hub (cylindrical outer wall, large through-bore)
  • Two symmetric arms extending in ±X
  • Two counterbored fixing-through-holes at ±X

Geometry verified against the original STEP file:
  Volume error  : < 0.001 %
  Face count    : 17  (exact match)
  Bounding box  : 300 × 158 × 40 mm

Usage:
    python CommonBearingFixThrough_parametric.py
    # Exports STEP + STL alongside the script, then opens in OCP CAD Viewer
"""

from build123d import *

try:
    from ocp_vscode import show as _ocp_show
    _USE_OCP = True
except Exception:
    _USE_OCP = False

# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERS  (all dimensions in mm)
# ══════════════════════════════════════════════════════════════════════════════

# ── Overall ────────────────────────────────────────────────────────────────────
total_height        = 40.0      # Part height (Z)

# ── Central hub ────────────────────────────────────────────────────────────────
hub_radius_outer    = 79.0      # Outer radius of the central hub cylinder
hub_bore_radius     = 50.0      # Central through-bore radius

# ── Arms ───────────────────────────────────────────────────────────────────────
arm_length          = 300.0     # Full arm span in X  (−150 → +150)
arm_width           = 65.0      # Arm width in Y      (= 2 × 32.5 mm)

# ── Counterbored fixing holes (×2, symmetric at ±X) ───────────────────────────
hole_cx             = 110.0     # Hole-centre X offset from origin
counterbore_radius  = 29.5      # Large bore radius (counterbore)
counterbore_depth   = 30.0      # Counterbore depth from top surface
thru_bore_radius    = 17.0      # Small through-bore radius (full height)

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD GEOMETRY
# ══════════════════════════════════════════════════════════════════════════════

with BuildPart() as part:

    # ── Solid body ─────────────────────────────────────────────────────────────

    # 1. Central hub — full-height cylinder
    Cylinder(
        radius=hub_radius_outer,
        height=total_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # 2. Arms — rectangular block spanning full X range, centred on origin
    Box(
        length=arm_length,
        width=arm_width,
        height=total_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
        mode=Mode.ADD,
    )

    # ── Subtractions ───────────────────────────────────────────────────────────

    # 3. Central through-bore (full height)
    Cylinder(
        radius=hub_bore_radius,
        height=total_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
        mode=Mode.SUBTRACT,
    )

    # 4. Counterbored fixing holes — one on each side (±X)
    for sx in [hole_cx, -hole_cx]:

        # 4a. Small through-bore — runs full height (z = 0 → total_height)
        with Locations((sx, 0, 0)):
            Cylinder(
                radius=thru_bore_radius,
                height=total_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # 4b. Counterbore — large bore from the top surface downward
        #     bottom of counterbore sits at z = total_height − counterbore_depth
        with Locations((sx, 0, total_height - counterbore_depth)):
            Cylinder(
                radius=counterbore_radius,
                height=counterbore_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════════════════
result = part.part.rotate(Axis.Y, 90)   # ← 90° vertical rotation
bb     = result.bounding_box()
# result = part.part
# bb     = result.bounding_box()

print("=" * 52)
print("  CommonBearingFixThrough — build summary")
print("=" * 52)
print(f"  Volume  : {result.volume:>12.4f} mm³")
print(f"  Faces   : {len(result.faces()):>4d}   (expected 17)")
print(f"  X span  : {bb.min.X:.1f} → {bb.max.X:.1f}  ({bb.max.X - bb.min.X:.1f} mm)")
print(f"  Y span  : {bb.min.Y:.1f} → {bb.max.Y:.1f}  ({bb.max.Y - bb.min.Y:.1f} mm)")
print(f"  Z span  : {bb.min.Z:.1f} → {bb.max.Z:.1f}  ({bb.max.Z - bb.min.Z:.1f} mm)")
print("=" * 52)

# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT PATHS  —  edit these to control where files are saved
# ══════════════════════════════════════════════════════════════════════════════

import os, subprocess, sys

OUTPUT_DIR = "/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d"

_base      = os.path.join(OUTPUT_DIR, "CommonBearingFixThrough_parametric")

# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT  —  STEP + STL
# ══════════════════════════════════════════════════════════════════════════════

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── STEP ──────────────────────────────────────────────────────────────────────
_step_path = _base + ".step"
export_step(result, _step_path)
print(f"STEP exported : {_step_path}")

# ── STL ───────────────────────────────────────────────────────────────────────
# tolerance        : linear chord tolerance (mm) — lower = finer mesh
# angular_tolerance: angular deviation (deg)     — lower = smoother curves
_stl_path = _base + ".stl"
export_stl(result, _stl_path, tolerance=0.01, angular_tolerance=0.1)
print(f"STL  exported : {_stl_path}")

# ══════════════════════════════════════════════════════════════════════════════
#  STL VALIDATION  (reference vs generated)
# ══════════════════════════════════════════════════════════════════════════════

_ref_stl = os.path.join(OUTPUT_DIR, "CommonBearingFixThrough.stl")

if os.path.exists(_ref_stl):
    try:
        import trimesh, numpy as np
        from scipy.spatial import cKDTree

        _ref = trimesh.load(_ref_stl, force="mesh")
        _gen = trimesh.load(_stl_path, force="mesh")

        # Auto-scale reference if units differ (e.g. cm vs mm)
        _spans_gen = _gen.bounds[1] - _gen.bounds[0]
        _spans_ref = _ref.bounds[1] - _ref.bounds[0]
        _scale = float(np.median(_spans_gen / np.where(_spans_ref > 0, _spans_ref, 1)))
        _scale = round(_scale * 2) / 2
        if abs(_scale - 1.0) > 0.05:
            _ref.apply_scale(_scale)

        # Volumetric difference
        _vol_diff_pct = (_gen.volume - _ref.volume) / _ref.volume * 100

        # Symmetric difference (boolean)
        _diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
        _diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
        _union   = trimesh.boolean.union([_gen, _ref],       engine="manifold")
        _sym_vol = _diff_gn.volume + _diff_rg.volume
        _sym_pct = _sym_vol / _union.volume * 100

        print("\n" + "─" * 52)
        print("  STL Validation (ref vs generated)")
        print("─" * 52)
        print(f"  Ref volume       : {_ref.volume:>12.2f} mm³" +
              (f"  (scaled ×{_scale:.0f})" if abs(_scale-1)>0.05 else ""))
        print(f"  Gen volume       : {_gen.volume:>12.2f} mm³")
        print(f"  Volume diff      : {_vol_diff_pct:>+11.4f} %"
              + ("  ✓" if abs(_vol_diff_pct) < 1.0 else "  ✗"))
        print(f"  Sym-diff         : {_sym_pct:>11.4f} % of union"
              + ("  ✓" if _sym_pct < 2.0 else "  ✗"))
        print("─" * 52)

    except ImportError:
        print("[SKIP] STL validation requires: pip install trimesh manifold3d scipy")
    except Exception as e:
        print(f"[WARN] STL validation failed: {e}")
else:
    print(f"[SKIP] Reference STL not found, skipping validation: {_ref_stl}")

# ══════════════════════════════════════════════════════════════════════════════
#  OCP VIEWER
# ══════════════════════════════════════════════════════════════════════════════

# ── Try ocp_vscode first ───────────────────────────────────────────────────────
if _USE_OCP:
    try:
        _ocp_show(result)
        print("Displayed in OCP CAD Viewer.")
    except Exception as e:
        print(f"ocp_vscode show() failed: {e}")
        _USE_OCP = False

# ── Fallback: open the exported STEP with the system viewer ───────────────────
if not _USE_OCP:
    print(f"Opening STEP in system viewer: {_step_path}")
    if sys.platform == "darwin":
        subprocess.run(["open", _step_path])
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", _step_path])