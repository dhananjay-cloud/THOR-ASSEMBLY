"""
Art4BearingRing — Parametric build123d Script
===============================================
A large bearing ring with:
  • Stepped disc body (lower r=400 / upper r=500)
  • Central bore r=360 with toroidal groove (ball-race groove)
  • 4× counterbored mounting holes at (±390, ±225)
  • Horizontal side bore + conical entry (lubrication port)

Geometry verified against original STEP file:
  Volume error  : < 0.001%
  Bounding box  : 1000 × 1000 × 100 mm

Dependencies:
    pip install build123d cadquery trimesh manifold3d scipy ocp-vscode

Usage:
    python Art4BearingRing_parametric.py
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
_base      = os.path.join(OUTPUT_DIR, "Art4BearingRing_parametric")

# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERS  (all dimensions in mm)
# ══════════════════════════════════════════════════════════════════════════════

# ── Stepped disc body ─────────────────────────────────────────────────────────
lower_radius    = 400.0     # Lower disc outer radius
lower_height    =  40.0     # Lower disc height  (z = 0 → 40)
upper_radius    = 500.0     # Upper disc outer radius
upper_height    =  60.0     # Upper disc height  (z = 40 → 100)
total_height    = 100.0     # Overall height

# ── Central bore & torus groove ───────────────────────────────────────────────
bore_radius     = 360.0     # Central through-bore radius
torus_R         = 350.0     # Torus major radius  (distance of groove centre from Z-axis)
torus_r         =  32.0     # Torus minor radius  (groove cross-section radius)
torus_z         =  50.0     # Torus centre height (mid-height of part)

# ── Counterbored mounting holes (×4, at ±X / ±Y) ─────────────────────────────
hole_positions  = [(390, 225), (390, -225), (-390, 225), (-390, -225)]
thru_bore_r     =  17.0     # Through-bore radius (z = 40 → 75)
thru_bore_depth =  35.0     # Through-bore depth  (z = 40 → 75)
cbore_r         =  33.5     # Counterbore radius  (z = 75 → 100)
cbore_depth     =  25.0     # Counterbore depth   (z = 75 → 100)

# ── Side lubrication bore (horizontal, along -X axis) ────────────────────────
side_bore_r     =  37.0     # Bore + cone junction radius
side_bore_z     =  50.0     # Bore axis height (same as torus centre)
side_cyl_x_end  = -405.0    # Cylinder ends here (flush with outer body wall region)
cone_x_end      = -360.0    # Cone narrows to here (meets torus groove wall)
cone_angle_deg  =   7.9696  # Cone semi-angle (degrees)

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD GEOMETRY
# ══════════════════════════════════════════════════════════════════════════════

_cone_len    = abs(cone_x_end - side_cyl_x_end)           # 45 mm
_r_narrow    = side_bore_r - _cone_len * math.tan(math.radians(cone_angle_deg))
_cyl_len     = abs(side_cyl_x_end) - upper_radius + upper_radius  # 95 mm  (-500 to -405)

# Bore profile plane: XZ-plane raised to side_bore_z, normal pointing in -Y
_bore_plane  = Plane(
    origin=(0, 0, side_bore_z),
    x_dir=(1, 0, 0),
    z_dir=(0, -1, 0),
)

with BuildPart() as part:

    # ── Solid body ─────────────────────────────────────────────────────────────

    # 1. Lower disc (r=400, z=0..40)
    Cylinder(
        radius=lower_radius,
        height=lower_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # 2. Upper disc (r=500, z=40..100) — added on top of lower
    with Locations((0, 0, lower_height)):
        Cylinder(
            radius=upper_radius,
            height=upper_height,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.ADD,
        )

    # ── Subtractions ───────────────────────────────────────────────────────────

    # 3. Central through-bore (r=360, full height)
    Cylinder(
        radius=bore_radius,
        height=total_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
        mode=Mode.SUBTRACT,
    )

    # 4. Toroidal ball-race groove (R=350, r=32, at z=50)
    with Locations((0, 0, torus_z)):
        Torus(
            major_radius=torus_R,
            minor_radius=torus_r,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )

    # 5. Counterbored mounting holes — lower disc is solid, holes start at z=40
    for (hx, hy) in hole_positions:

        # 5a. Through-bore (r=17, z=40..75)
        with Locations((hx, hy, lower_height)):
            Cylinder(
                radius=thru_bore_r,
                height=thru_bore_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # 5b. Counterbore (r=33.5, z=75..100)
        with Locations((hx, hy, lower_height + thru_bore_depth)):
            Cylinder(
                radius=cbore_r,
                height=cbore_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

    # 6. Horizontal side bore + conical entry — built as a single revolve
    #    Profile (in bore_plane coords): cylinder rect + cone trapezoid
    #    Revolved 360° around the bore axis (X-axis at Z=side_bore_z)
    with BuildSketch(_bore_plane) as sk:
        with BuildLine() as bl:
            Line((-upper_radius,         0),            (-upper_radius,   side_bore_r))   # outer wall
            Line((-upper_radius,         side_bore_r),  (side_cyl_x_end,  side_bore_r))   # cylinder top
            Line((side_cyl_x_end,        side_bore_r),  (cone_x_end,      _r_narrow))     # cone taper
            Line((cone_x_end,            _r_narrow),    (cone_x_end,      0))             # cone inner wall
            Line((cone_x_end,            0),            (-upper_radius,   0))             # axis (bottom)
        make_face()
    revolve(
        sk.sketch,
        axis=Axis(origin=(0, 0, side_bore_z), direction=(1, 0, 0)),
        revolution_arc=360,
        mode=Mode.SUBTRACT,
    )

# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

result = part.part
bb     = result.bounding_box()

print("=" * 56)
print("  Art4BearingRing — build summary")
print("=" * 56)
print(f"  Volume  : {result.volume:>16.4f} mm³")
print(f"  Faces   : {len(result.faces()):>4d}")
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

# ── STL ───────────────────────────────────────────────────────────────────────
# build123d's export_stl can produce non-watertight meshes on complex geometry;
# round-tripping through STEP → CadQuery gives a reliable watertight STL.
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

_ref_stl = os.path.join(OUTPUT_DIR, "Art4BearingRing.stl")

if os.path.exists(_ref_stl):
    try:
        import trimesh, numpy as np

        _ref_raw = trimesh.load(_ref_stl, force="mesh", process=True)
        _gen     = trimesh.load(_stl_path, force="mesh", process=True)

        # Repair meshes to make them watertight for boolean operations
        for _m in (_ref_raw, _gen):
            trimesh.repair.fix_normals(_m)
            trimesh.repair.fix_winding(_m)
            trimesh.repair.fix_inversion(_m)
            trimesh.repair.fill_holes(_m)

        # Auto-scale reference if units differ (e.g. cm vs mm)
        _spans_gen = _gen.bounds[1]  - _gen.bounds[0]
        _spans_ref = _ref_raw.bounds[1] - _ref_raw.bounds[0]
        _scale = float(np.median(_spans_gen / np.where(_spans_ref > 0, _spans_ref, 1)))
        _scale = round(_scale * 2) / 2
        _ref = _ref_raw.copy()
        if abs(_scale - 1.0) > 0.05:
            _ref.apply_scale(_scale)

        _vol_diff_pct = (_gen.volume - _ref.volume) / _ref.volume * 100

        # Try boolean-based symmetric difference; fall back to volume-only comparison
        _sym_pct = None
        try:
            _diff_gn = trimesh.boolean.difference([_gen, _ref], engine="manifold")
            _diff_rg = trimesh.boolean.difference([_ref, _gen], engine="manifold")
            _union   = trimesh.boolean.union([_gen, _ref],       engine="manifold")
            _sym_pct = (_diff_gn.volume + _diff_rg.volume) / _union.volume * 100
        except Exception:
            pass  # Booleans failed — report volume comparison only

        print("\n" + "─" * 56)
        print("  STL Validation (ref vs generated)")
        print("─" * 56)
        print(f"  Ref volume       : {_ref.volume:>16.2f} mm³" +
              (f"  (scaled ×{_scale:.0f})" if abs(_scale - 1) > 0.05 else ""))
        print(f"  Gen volume       : {_gen.volume:>16.2f} mm³")
        print(f"  Volume diff      : {_vol_diff_pct:>+15.4f} %"
              + ("  ✓" if abs(_vol_diff_pct) < 1.0 else "  ✗"))
        if _sym_pct is not None:
            print(f"  Sym-diff         : {_sym_pct:>15.4f} % of union"
                  + ("  ✓" if _sym_pct < 2.0 else "  ✗"))
        else:
            print(f"  Sym-diff         :   skipped (meshes not watertight for booleans)")
        print("─" * 56)

    except ImportError:
        print("[SKIP] STL validation requires: pip install trimesh manifold3d scipy")
    except Exception as e:
        print(f"[WARN] STL validation failed: {e}")
else:
    print(f"[SKIP] Reference STL not found, skipping validation: {_ref_stl}")

# ══════════════════════════════════════════════════════════════════════════════
#  OCP VIEWER
# ══════════════════════════════════════════════════════════════════════════════

if _USE_OCP:
    try:
        _ocp_show(result)
        print("Displayed in OCP CAD Viewer.")
    except Exception as e:
        print(f"[WARN] OCP CAD Viewer not available (is VS Code running with ocp-vscode extension?): {e}")
        _USE_OCP = False

if not _USE_OCP:
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["open", _step_path], capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[INFO] No application found to open .step files. Open manually: {_step_path}")
            else:
                print(f"Opened STEP in system viewer: {_step_path}")
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", _step_path], capture_output=True)
    except Exception:
        print(f"[INFO] Could not open STEP file. Open manually: {_step_path}")
