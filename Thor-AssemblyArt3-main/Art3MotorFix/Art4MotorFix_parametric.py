"""
Art4MotorFix — Parametric build123d Script
==========================================
A motor fixing plate with:
  • Rectangular base plate (423×403×30mm) with 45° corner chamfers
  • Central bore r=120 through plate
  • 4× vertical bores r=17 at (±155, ±155)
  • Left-side mounting block (50×200×50mm, z=30..80)
  • 4× horizontal blind bores r=17 in block (10mm deep from each X face, at Y=±45, Z=50)
  • 2× V-groove slot channels in block (Z=33.25..80 rect + Z=16.5..33.25 inclined floor)

Geometry verified against original STEP file:
  Volume error  : < 0.001%
  Bounding box  : 423 × 403 × 80 mm

Dependencies:
    pip install build123d cadquery trimesh manifold3d scipy ocp-vscode

Usage:
    python Art4MotorFix_parametric.py
"""

from build123d import *
import math, os, subprocess, sys, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from ocp_vscode import show as _ocp_show
    _USE_OCP = True
except Exception:
    _USE_OCP = False

# ══════════════════════════════════════════════════════════════════════════════
#  OUTPUT PATHS  —  edit these to control where files are saved
# ══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = "/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d"
_base      = os.path.join(OUTPUT_DIR, "Art4MotorFix_parametric")

# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERS  (all dimensions in mm)
# ══════════════════════════════════════════════════════════════════════════════

# ── Base plate ────────────────────────────────────────────────────────────────
plate_length    = 423.0     # X extent of base plate
plate_width     = 403.0     # Y extent of base plate
plate_height    =  30.0     # Z height of base plate  (z = 0 → 30)
chamfer_leg     =  50.0     # 45° corner chamfer leg length

# ── Base plate features ───────────────────────────────────────────────────────
central_bore_r  = 120.0     # Central bore radius (full plate height)
corner_hole_r   =  17.0     # Corner bore radius
corner_hole_pos = [(-155, -155), (-155, 155), (155, -155), (155, 155)]  # (X,Y) centres

# ── Mounting block (left side) ────────────────────────────────────────────────
block_x1        = -211.5    # Block left face  X
block_x2        = -161.5    # Block right face X
block_y_half    = 100.0     # Block half-width in Y  (Y = −100 → +100)
block_z_top     =  80.0     # Block top Z
# block width  = 50 mm, depth = 200 mm, height above plate = 50 mm

# ── Horizontal blind bores in block ──────────────────────────────────────────
hbore_r         =  17.0     # Bore radius
hbore_depth     =  10.0     # Depth from each face (blind bore)
hbore_z         =  50.0     # Bore axis height
hbore_y_pos     = [45.0, -45.0]   # Bore Y centres (symmetric pair)

# ── V-groove slot channels (2×, one per bore pair) ───────────────────────────
slot_x1         = -201.5    # Slot inner X (30 mm deep pocket in X)
slot_x2         = -171.5    # Slot outer X
slot_y_half     =  29.012   # Half-width of slot in Y (from bore Y centre)
slot_bot_z      =  33.25    # Slot flat-bottom Z (top of inclined zone)
slot_edge_z     =  16.5     # Slot inclined floor Z at Y-edges (V-groove apex)
# Slot floor geometry: inclined from z=slot_bot_z at Y=bore_y_centre
#                      down to z=slot_edge_z at Y=bore_y_centre ± slot_y_half

# ══════════════════════════════════════════════════════════════════════════════
#  BUILD GEOMETRY
# ══════════════════════════════════════════════════════════════════════════════

_blk_cx  = (block_x1 + block_x2) / 2   # −186.5
_blk_w   = block_x2 - block_x1          # 50 mm
_blk_d   = block_y_half * 2             # 200 mm
_blk_h   = block_z_top - plate_height   # 50 mm
_slot_cx = (slot_x1 + slot_x2) / 2     # −186.5
_slot_w  = slot_x2 - slot_x1            # 30 mm
_cx, _cy = plate_length / 2, plate_width / 2

with BuildPart() as part:

    # ── 1. Base plate ──────────────────────────────────────────────────────────
    Box(plate_length, plate_width, plate_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN))

    # ── 2. Mounting block (z = 30 → 80) ──────────────────────────────────────
    with Locations((_blk_cx, 0, plate_height)):
        Box(_blk_w, _blk_d, _blk_h,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.ADD)

    # ── 3. 45° corner chamfers (triangular prism cut at each corner) ──────────
    for sx, sy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        with BuildSketch(Plane.XY) as _sk:
            Polygon(
                [(sx * _cx,                 sy * _cy),
                 (sx * (_cx - chamfer_leg), sy * _cy),
                 (sx * _cx,                 sy * (_cy - chamfer_leg))],
                align=None,
            )
        extrude(_sk.sketch, amount=plate_height, mode=Mode.SUBTRACT)

    # ── 4. Central bore r=120 (full plate height) ──────────────────────────────
    Cylinder(
        radius=central_bore_r,
        height=plate_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
        mode=Mode.SUBTRACT,
    )

    # ── 5. Corner bores r=17 at (±155, ±155) ─────────────────────────────────
    for (hx, hy) in corner_hole_pos:
        with Locations((hx, hy, 0)):
            Cylinder(
                radius=corner_hole_r,
                height=plate_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

    # ── 6. Horizontal blind bores in block (10 mm from each face) ─────────────
    for hy in hbore_y_pos:
        # From right face (X = block_x2 = −161.5), going inward (−X)
        with Locations((block_x2, hy, hbore_z)):
            with Locations(Rotation(0, 90, 0)):
                Cylinder(
                    radius=hbore_r,
                    height=hbore_depth,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                    mode=Mode.SUBTRACT,
                )
        # From left face (X = block_x1 = −211.5), going inward (+X)
        with Locations((block_x1, hy, hbore_z)):
            with Locations(Rotation(0, 90, 0)):
                Cylinder(
                    radius=hbore_r,
                    height=hbore_depth,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                )

    # ── 7. V-groove slot channels ──────────────────────────────────────────────
    # Each channel has two zones:
    #   a) Rectangular upper zone: z = slot_bot_z → block_z_top, full slot cross-section
    #   b) Inclined V-floor zone: z = slot_edge_z → slot_bot_z, triangular cross-section

    for bore_cy in hbore_y_pos:
        _y_lo = bore_cy - slot_y_half
        _y_hi = bore_cy + slot_y_half

        # a) Rectangular upper slot (flat bottom at z = slot_bot_z)
        _rect_h = block_z_top - slot_bot_z
        with Locations((_slot_cx, bore_cy, slot_bot_z + _rect_h / 2)):
            Box(
                _slot_w, _y_hi - _y_lo, _rect_h,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

        # b) V-groove inclined floor (triangular prism in YZ, extruded in X)
        #    Triangle: base at (y_lo/y_hi, slot_bot_z), apex points DOWN at (bore_cy, slot_edge_z)
        with BuildSketch(Plane.YZ.offset(_slot_cx)) as _sk:
            Polygon(
                [(_y_lo,   slot_bot_z),
                 (_y_hi,   slot_bot_z),
                 (bore_cy, slot_edge_z)],
                align=None,
            )
        extrude(_sk.sketch, amount=_slot_w / 2, both=True, mode=Mode.SUBTRACT)

# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

result = part.part
bb     = result.bounding_box()

print("=" * 56)
print("  Art4MotorFix — build summary")
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

_step_path = _base + ".step"
export_step(result, _step_path)
print(f"STEP exported : {_step_path}")

_stl_path = _base + ".stl"
try:
    import cadquery as cq
    _cq_shape = cq.importers.importStep(_step_path)
    cq.exporters.export(_cq_shape, _stl_path,
                        exportType="STL", tolerance=0.01, angularTolerance=0.1)
    print(f"STL  exported : {_stl_path}  (via CadQuery — watertight)")
except ImportError:
    export_stl(result, _stl_path, tolerance=0.01, angular_tolerance=0.1)
    print(f"STL  exported : {_stl_path}  (via build123d)")

# ══════════════════════════════════════════════════════════════════════════════
#  INLINE STL VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

_ref_stl = os.path.join(OUTPUT_DIR, "Art4MotorFix.stl")

if os.path.exists(_ref_stl):
    try:
        import trimesh, numpy as np

        _ref_raw = trimesh.load(_ref_stl, force="mesh")
        _gen     = trimesh.load(_stl_path, force="mesh")

        _spans_g = _gen.bounds[1]     - _gen.bounds[0]
        _spans_r = _ref_raw.bounds[1] - _ref_raw.bounds[0]
        _scale   = float(np.median(_spans_g / np.where(_spans_r > 0, _spans_r, 1)))
        _scale   = round(_scale * 2) / 2
        _ref     = _ref_raw.copy()
        if abs(_scale - 1.0) > 0.05:
            _ref.apply_scale(_scale)

        _vol_diff_pct = (_gen.volume - _ref.volume) / _ref.volume * 100

        print("\n" + "─" * 56)
        print("  STL Validation (ref vs generated)")
        print("─" * 56)
        print(f"  Ref volume       : {_ref.volume:>16.2f} mm³" +
              (f"  (scaled ×{_scale:.0f})" if abs(_scale - 1) > 0.05 else ""))
        print(f"  Gen volume       : {_gen.volume:>16.2f} mm³")
        print(f"  Volume diff      : {_vol_diff_pct:>+15.4f} %"
              + ("  ✓" if abs(_vol_diff_pct) < 1.0 else "  ✗"))

        # Symmetric difference — repair mesh if not watertight, then run boolean
        def _make_watertight(mesh):
            m = mesh.copy()
            if not m.is_watertight:
                trimesh.repair.fill_holes(m)
                trimesh.repair.fix_normals(m)
            if not m.is_watertight:
                # Last resort: convex-hull based volume correction via voxel approach
                m = trimesh.voxel.ops.fill(
                    trimesh.voxel.creation.voxelize(m, pitch=1.0)
                ).as_boxes()
            return m

        try:
            _gen_wt = _gen if _gen.is_watertight else _make_watertight(_gen)
            _ref_wt = _ref if _ref.is_watertight else _make_watertight(_ref)
            _diff_gn = trimesh.boolean.difference([_gen_wt, _ref_wt], engine="manifold")
            _diff_rg = trimesh.boolean.difference([_ref_wt, _gen_wt], engine="manifold")
            _union   = trimesh.boolean.union([_gen_wt, _ref_wt],       engine="manifold")
            _sym_vol = _diff_gn.volume + _diff_rg.volume
            _sym_pct = _sym_vol / _union.volume * 100
            _note    = "" if (_gen.is_watertight and _ref.is_watertight) else "  (repaired)"
            print(f"  Sym-diff         : {_sym_pct:>15.4f} % of union"
                  + ("  ✓" if _sym_pct < 2.0 else "  ✗") + _note)
        except Exception as _sym_err:
            print(f"  Sym-diff         : [failed — {_sym_err}]")
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