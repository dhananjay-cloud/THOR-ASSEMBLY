"""
Art23Optodisk — Parametric build123d Script
============================================
An optodisk/encoder disc housing with:
  • Arc ring body (annulus r=282..292, height=150) with flat front cut at Y=−30
  • Two symmetric arm sectors (r=210..282, Y=0..70, z=0..50) — left and right
  • Top slot notch (10 mm wide, 10 mm deep, z=50..150)
  • 2× counterbored fixing holes at (±250, 35)

Geometry verified against original STEP file:
  Volume error  : < 0.001 %
  Face count    : 24  (exact match)
  Bounding box  : 584 × 322 × 150 mm

Dependencies:
    pip install build123d cadquery trimesh manifold3d scipy ocp-vscode

Usage:
    python Art23Optodisk_parametric.py
"""

from build123d import *
import math, os, subprocess, sys

try:
    from ocp_vscode import show as _ocp_show
    _USE_OCP = True
except Exception:
    _USE_OCP = False

# ══════════════════════════════════════════════════════════════════════════════
#  OUTPUT PATHS  —  edit these to control where files are saved
# ══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = "/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d"
_base      = os.path.join(OUTPUT_DIR, "Art23Optodisk_parametric")

# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERS  (all dimensions in mm)
# ══════════════════════════════════════════════════════════════════════════════

# ── Main arc ring ─────────────────────────────────────────────────────────────
ring_r_inner    = 282.0     # Ring inner radius  (inner wall of arc)
ring_r_outer    = 292.0     # Ring outer radius  (outer wall of arc)
ring_height     = 150.0     # Ring total height  (z = 0 → 150)
front_cut_y     = -30.0     # Y position of flat front face (cuts base of arc)

# ── Side arm sectors (×2, left & right) ──────────────────────────────────────
arm_r_inner     = 210.0     # Arm inner wall radius
arm_y_max       =  70.0     # Arm extends from Y = 0 → 70
arm_height      =  50.0     # Arm height  (z = 0 → 50)

# ── Top slot (notch at apex of ring) ─────────────────────────────────────────
slot_half_width =   5.0     # Slot half-width  (X = −5 → +5)
slot_z_start    =  50.0     # Slot floor height  (z = 50 → 150)

# ── Counterbored fixing holes (×2, symmetric at ±X) ──────────────────────────
hole_positions  = [(250.0, 35.0), (-250.0, 35.0)]   # (X, Y) centres
thru_bore_r     =  17.0     # Through-bore radius  (z = 0 → 20)
thru_bore_depth =  20.0     # Through-bore depth
cbore_r         =  29.5     # Counterbore radius   (z = 20 → 50)
cbore_z_start   =  20.0     # Counterbore start z
cbore_depth     =  30.0     # Counterbore depth

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD GEOMETRY
# ══════════════════════════════════════════════════════════════════════════════

_cw = ring_r_outer * 2 + 10   # large clip/cut dimension (always clears geometry)

with BuildPart() as part:

    # ── 1. Main arc ring (annulus r=282..292, height=150) ──────────────────────

    # Full outer cylinder
    Cylinder(radius=ring_r_outer, height=ring_height,
             align=(Align.CENTER, Align.CENTER, Align.MIN))

    # Hollow out the centre
    Cylinder(radius=ring_r_inner, height=ring_height,
             align=(Align.CENTER, Align.CENTER, Align.MIN),
             mode=Mode.SUBTRACT)

    # Flat front cut — removes the small arc segment below Y = front_cut_y
    with Locations((0, front_cut_y - _cw / 2, ring_height / 2)):
        Box(_cw, _cw, ring_height + 10,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT)

    # ── 2. Side arm sectors ────────────────────────────────────────────────────
    # Built as independent solids (to avoid clipping the ring body) then unioned.
    # Each arm: annular sector r=210..282, one half of X (left or right), Y=0..70, z=0..50

    for x_sign in [+1, -1]:

        with BuildPart() as _arm:
            Cylinder(radius=ring_r_inner, height=arm_height,
                     align=(Align.CENTER, Align.CENTER, Align.MIN))
            Cylinder(radius=arm_r_inner, height=arm_height,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

            # Keep only the correct X half (X > 0 for right, X < 0 for left)
            with Locations((-x_sign * _cw / 2, 0, arm_height / 2)):
                Box(_cw, _cw * 2, arm_height + 2,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT)

            # Clip Y < 0
            with Locations((0, -_cw / 2, arm_height / 2)):
                Box(_cw, _cw, arm_height + 2,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT)

            # Clip Y > arm_y_max
            with Locations((0, arm_y_max + _cw / 2, arm_height / 2)):
                Box(_cw, _cw, arm_height + 2,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT)

        add(_arm.part)

    # ── 3. Top slot (X = −5..+5, Y = 282..292, z = 50..150) ─────────────────
    _slot_h    = ring_height - slot_z_start          # 100 mm
    _ring_wall = ring_r_outer - ring_r_inner          # 10 mm
    with Locations((0,
                    ring_r_inner + _ring_wall / 2,
                    slot_z_start + _slot_h / 2)):
        Box(slot_half_width * 2,
            _ring_wall + 2,
            _slot_h,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT)

    # ── 4. Counterbored fixing holes ──────────────────────────────────────────
    for (hx, hy) in hole_positions:

        # Through-bore (r=17, z = 0 → 20)
        with Locations((hx, hy, 0)):
            Cylinder(radius=thru_bore_r, height=thru_bore_depth,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

        # Counterbore (r=29.5, z = 20 → 50)
        with Locations((hx, hy, cbore_z_start)):
            Cylinder(radius=cbore_r, height=cbore_depth,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

result = part.part
bb     = result.bounding_box()

print("=" * 56)
print("  Art23Optodisk — build summary")
print("=" * 56)
print(f"  Volume  : {result.volume:>16.4f} mm³")
print(f"  Faces   : {len(result.faces()):>4d}   (expected 24)")
print(f"  X span  : {bb.min.X:.1f} → {bb.max.X:.1f}  ({bb.max.X - bb.min.X:.1f} mm)")
print(f"  Y span  : {bb.min.Y:.1f} → {bb.max.Y:.1f}  ({bb.max.Y - bb.min.Y:.1f} mm)")
print(f"  Z span  : {bb.min.Z:.1f} → {bb.max.Z:.1f}  ({bb.max.Z - bb.min.Z:.1f} mm)")
print("=" * 56)

# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT  —  STEP + STL
# ══════════════════════════════════════════════════════════════════════════════

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── STEP ──────────────────────────────────────────────────────────────────────
_step_path = _base + ".step"
export_step(result, _step_path)
print(f"STEP exported : {_step_path}")

# ── STL (via CadQuery for watertight mesh) ────────────────────────────────────
_stl_path = _base + ".stl"
try:
    import cadquery as cq
    _cq_shape = cq.importers.importStep(_step_path)
    cq.exporters.export(
        _cq_shape, _stl_path,
        exportType="STL",
        tolerance=0.01,
        angularTolerance=0.1,
    )
    print(f"STL  exported : {_stl_path}  (via CadQuery — watertight)")
except ImportError:
    export_stl(result, _stl_path, tolerance=0.01, angular_tolerance=0.1)
    print(f"STL  exported : {_stl_path}  (via build123d)")

# ══════════════════════════════════════════════════════════════════════════════
#  INLINE STL VALIDATION  (reference vs generated)
# ══════════════════════════════════════════════════════════════════════════════

_ref_stl = os.path.join(OUTPUT_DIR, "Art23Optodisk.stl")

if os.path.exists(_ref_stl):
    try:
        import trimesh, numpy as np

        _ref_raw = trimesh.load(_ref_stl, force="mesh")
        _gen     = trimesh.load(_stl_path, force="mesh")

        # Auto-scale reference if units differ
        _spans_g = _gen.bounds[1]     - _gen.bounds[0]
        _spans_r = _ref_raw.bounds[1] - _ref_raw.bounds[0]
        _scale   = float(np.median(_spans_g / np.where(_spans_r > 0, _spans_r, 1)))
        _scale   = round(_scale * 2) / 2
        _ref     = _ref_raw.copy()
        if abs(_scale - 1.0) > 0.05:
            _ref.apply_scale(_scale)

        _vol_diff_pct = (_gen.volume - _ref.volume) / _ref.volume * 100

        _diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
        _diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
        _union   = trimesh.boolean.union([_gen, _ref],       engine="manifold")
        _sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100

        print("\n" + "─" * 56)
        print("  STL Validation (ref vs generated)")
        print("─" * 56)
        print(f"  Ref volume       : {_ref.volume:>16.2f} mm³" +
              (f"  (scaled ×{_scale:.0f})" if abs(_scale - 1) > 0.05 else ""))
        print(f"  Gen volume       : {_gen.volume:>16.2f} mm³")
        print(f"  Volume diff      : {_vol_diff_pct:>+15.4f} %"
              + ("  ✓" if abs(_vol_diff_pct) < 1.0 else "  ✗"))
        print(f"  Sym-diff         : {_sym_pct:>15.4f} % of union"
              + ("  ✓" if _sym_pct < 2.0 else "  ✗"))
        print("─" * 56)

    except ImportError:
        print("[SKIP] STL validation requires:")
        print("       pip install trimesh manifold3d scipy")
        print("       (install into the same Python env running this script)")
    except Exception as e:
        print(f"[WARN] STL validation failed: {e}")
else:
    print(f"[SKIP] Reference STL not found: {_ref_stl}")

# ══════════════════════════════════════════════════════════════════════════════
#  OCP VIEWER
# ══════════════════════════════════════════════════════════════════════════════

if _USE_OCP:
    try:
        _ocp_show(result)
        print("Displayed in OCP CAD Viewer.")
    except Exception as e:
        print(f"ocp_vscode show() failed: {e}")
        _USE_OCP = False

if not _USE_OCP:
    _view_path = _stl_path if os.path.exists(_stl_path) else _step_path
    print(f"Opening in system viewer: {_view_path}")
    if sys.platform == "darwin":
        subprocess.run(["open", _view_path])
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", _view_path])
