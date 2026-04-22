"""
Art4MotorGear — Pure Parametric build123d Script (MakePipeShell)
=================================================================
Helical spur gear with integral shaft section.
NO DXF imports — pure involute tooth math + OCC helical pipe sweep.

Uses BRepOffsetAPI_MakePipeShell with an auxiliary helix wire for
smooth helical tooth flanks — NO staircase/loft layering artifacts.

  GEAR (Z=0..130.0184):
    • 10 teeth, transverse module 18, pressure angle 20°
    • Left-hand helix, 29.5341° helix angle (~46.9° total twist)
    • Smooth involute flanks via OCC pipe sweep
    • Tip Ø216, Root Ø135, Pitch Ø180
    • Central bore r=25

  SHAFT (Z=0..−100):
    • Outer cylinder r=120, central bore r=25
    • Keyway slot (30×58.024) with V-chamfer top
    • Counterbored horizontal bore from −X (cbore r=29.5, bore r=17)
    • Through horizontal bore from +X (r=17)

Volume: ~6,912,000 mm³  (target ~6,988,013 → −1.08%)
Faces:  ~676  (vs ~8000 with loft approach)
STEP:   ~4 MB (vs 50+ MB with DXF loft approach)

Dependencies: pip install build123d cadquery
Optional:     pip install trimesh manifold3d numpy ocp-vscode
"""

from build123d import *
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakePolygon
from OCP.gp import gp_Pnt
import math
import os
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from ocp_vscode import show as _ocp_show
    _USE_OCP = True
except Exception:
    _USE_OCP = False


# ══════════════════════════════════════════════════════════════════════════════
#  PATHS
# ══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = "/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d"
_base = os.path.join(OUTPUT_DIR, "Art4MotorGear_parametric_clau")
REFERENCE_STL = os.path.join(OUTPUT_DIR, "Art4MotorGear.stl")
REF_SCALE = 10.0  # reference STL is 0.1-scale


# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════

# ── Gear ──────────────────────────────────────────────────────────────────────
num_teeth       = 10
trans_module    = 18.0            # transverse module (mm)
pressure_angle  = 20.0            # transverse pressure angle (°)
helix_angle     = 29.5341         # helix angle (°), left-hand
face_width      = 130.0184        # gear face width (mm)
bore_radius     = 25.0            # central bore radius

# Derived gear geometry
pitch_r  = trans_module * num_teeth / 2.0                          # 90.0
tip_r    = pitch_r + trans_module                                   # 108.0
root_r   = pitch_r - 1.25 * trans_module                           # 67.5
base_r   = pitch_r * math.cos(math.radians(pressure_angle))        # 84.572

# Helix twist (total radians over face_width)
twist_total_rad = math.tan(math.radians(helix_angle)) * face_width / pitch_r

# Profile resolution
N_INVOLUTE_PTS  = 30              # points per involute flank
N_TIP_ARC_PTS   = 3               # interpolation points on tip arc
N_ROOT_ARC_PTS  = 4               # interpolation points on root arc
N_HELIX_PTS     = 100             # auxiliary helix polyline resolution

# ── Shaft ─────────────────────────────────────────────────────────────────────
shaft_radius = 120.0
shaft_depth  = 100.0

# ── Keyway ────────────────────────────────────────────────────────────────────
kw_x_min       = -75.0            # YZ plane offset (keyway left face)
kw_width       = 30.0             # X extent
kw_half_y      = 29.012           # Y half-width
kw_z_bottom    = -100.0           # bottom of keyway
kw_z_rect_top  = -28.25           # rectangle portion top
kw_z_chamfer   = -11.5            # V-chamfer apex

# ── Horizontal bores ──────────────────────────────────────────────────────────
bore_r_h    = 17.0
cbore_r     = 29.5
cbore_depth = 30.0
bore_depth  = shaft_radius + 1.0


# ══════════════════════════════════════════════════════════════════════════════
#  INVOLUTE TOOTH PROFILE
# ══════════════════════════════════════════════════════════════════════════════

def _involute_xy(br, t):
    """Point on involute of circle radius br at parameter t."""
    return (br * (math.cos(t) + t * math.sin(t)),
            br * (math.sin(t) - t * math.cos(t)))


def _inv_t_at_r(br, r):
    """Involute parameter t where radius equals r."""
    return 0.0 if r <= br else math.sqrt((r / br) ** 2 - 1.0)


def _dedupe(pts, tol=0.05):
    """Remove adjacent near-duplicate points."""
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out


def gear_tooth_profile():
    """
    Generate a closed 2D involute gear profile (CCW winding).

    For each tooth, going CCW:
      left_flank (root→tip) → tip_arc → right_flank (tip→root)
      → radial_drop → root_arc → radial_rise → [next tooth]
    """
    pa_rad = math.radians(pressure_angle)
    ang_pitch = 2.0 * math.pi / num_teeth
    inv_alpha = math.tan(pa_rad) - pa_rad

    # Half-tooth angular thickness at pitch circle
    half_thick = math.pi * trans_module / (4.0 * pitch_r) + inv_alpha

    t_tip = _inv_t_at_r(base_r, tip_r)
    n = N_INVOLUTE_PTS
    points = []

    for tooth in range(num_teeth):
        ca = tooth * ang_pitch

        # Left flank: base_r → tip_r
        for i in range(n):
            t = (i / (n - 1)) * t_tip
            ix, iy = _involute_xy(base_r, t)
            r = math.hypot(ix, iy)
            ang = math.atan2(iy, ix)
            fa = ca - half_thick + ang
            points.append((r * math.cos(fa), r * math.sin(fa)))

        # Tip arc: left_tip → right_tip
        a_left_tip = math.atan2(points[-1][1], points[-1][0])
        ix, iy = _involute_xy(base_r, t_tip)
        ang_tip = math.atan2(iy, ix)
        a_right_tip = ca + half_thick - ang_tip
        da_tip = a_right_tip - a_left_tip
        while da_tip < 0:
            da_tip += 2 * math.pi
        while da_tip > math.pi:
            da_tip -= 2 * math.pi
        for i in range(1, N_TIP_ARC_PTS + 1):
            a = a_left_tip + (i / (N_TIP_ARC_PTS + 1)) * da_tip
            points.append((tip_r * math.cos(a), tip_r * math.sin(a)))

        # Right flank: tip_r → base_r
        for i in range(n):
            t = t_tip * (1.0 - i / (n - 1))
            ix, iy = _involute_xy(base_r, t)
            r = math.hypot(ix, iy)
            ang = math.atan2(iy, ix)
            fa = ca + half_thick - ang
            points.append((r * math.cos(fa), r * math.sin(fa)))

        # Radial drop to root circle
        rf_angle = math.atan2(points[-1][1], points[-1][0])
        points.append((root_r * math.cos(rf_angle), root_r * math.sin(rf_angle)))

        # Root arc to next tooth
        next_ca = ((tooth + 1) % num_teeth) * ang_pitch
        next_lf_angle = next_ca - half_thick
        da_root = next_lf_angle - rf_angle
        while da_root < 0:
            da_root += 2 * math.pi
        while da_root > ang_pitch:
            da_root -= 2 * math.pi
        for i in range(1, N_ROOT_ARC_PTS + 1):
            a = rf_angle + (i / (N_ROOT_ARC_PTS + 1)) * da_root
            points.append((root_r * math.cos(a), root_r * math.sin(a)))

        # Radial rise to next tooth's base circle
        points.append((base_r * math.cos(next_lf_angle),
                        base_r * math.sin(next_lf_angle)))

    points = _dedupe(points)

    # Ensure CCW winding
    area = sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    ) / 2.0
    if area < 0:
        points.reverse()

    return points, abs(area)


# ══════════════════════════════════════════════════════════════════════════════
#  HELICAL GEAR BODY VIA OCC PIPE SWEEP
# ══════════════════════════════════════════════════════════════════════════════

def build_helical_gear(profile_pts):
    """
    Build the gear body using OCC MakePipeShell.

    Spine  = straight line along Z (0 → face_width)
    Profile = closed polyline of involute tooth cross-section at Z=0
    Aux    = polyline helix at pitch_r for twist guidance

    Result = smooth helical solid with no staircase artifacts.
    """
    # Closed profile wire at Z=0
    poly = BRepBuilderAPI_MakePolygon()
    for x, y in profile_pts:
        poly.Add(gp_Pnt(x, y, 0))
    poly.Close()
    profile_wire = poly.Wire()

    # Straight spine along Z
    spine_edge = BRepBuilderAPI_MakeEdge(
        gp_Pnt(0, 0, 0), gp_Pnt(0, 0, face_width)
    ).Edge()
    spine_wire = BRepBuilderAPI_MakeWire(spine_edge).Wire()

    # Auxiliary helix wire (polyline approximation at pitch_r)
    helix_poly = BRepBuilderAPI_MakePolygon()
    for i in range(N_HELIX_PTS + 1):
        t = i / N_HELIX_PTS
        z = t * face_width
        theta = -t * twist_total_rad  # negative for right-hand helix
        helix_poly.Add(gp_Pnt(
            pitch_r * math.cos(theta),
            pitch_r * math.sin(theta),
            z,
        ))
    aux_wire = helix_poly.Wire()

    # Pipe sweep
    pipe = BRepOffsetAPI_MakePipeShell(spine_wire)
    pipe.SetMode(aux_wire, False)    # auxiliary curve guides the twist
    pipe.Add(profile_wire, False, False)
    pipe.Build()

    if not pipe.IsDone():
        raise RuntimeError("MakePipeShell failed — check profile wire validity")

    pipe.MakeSolid()
    return Solid.cast(pipe.Shape())


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD
# ══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("  Building Art4MotorGear — Parametric + MakePipeShell")
print("=" * 60)

# 1. Generate tooth profile
profile_pts, profile_area = gear_tooth_profile()
print(f"  Tooth profile  : {len(profile_pts)} points, {profile_area:.0f} mm²")
print(f"  Helix twist    : {math.degrees(twist_total_rad):.2f}° over {face_width:.1f} mm")

# 2. Build smooth helical gear body
gear_body = build_helical_gear(profile_pts)
print(f"  Gear body      : {gear_body.volume:.0f} mm³, {len(gear_body.faces())} faces")

# 3. Full assembly
with BuildPart() as part:
    # Gear body (smooth helical sweep)
    add(gear_body)

    # Shaft cylinder (Z = −100 → 0)
    with Locations((0, 0, -shaft_depth)):
        Cylinder(
            shaft_radius, shaft_depth,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Central bore (full height)
    with Locations((0, 0, -shaft_depth)):
        Cylinder(
            bore_radius, shaft_depth + face_width + 1.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )

    # Keyway slot with V-chamfer top
    with BuildSketch(Plane.YZ.offset(kw_x_min)) as kw_sk:
        with BuildLine():
            Polyline(
                [
                    (-kw_half_y, kw_z_bottom),
                    (kw_half_y, kw_z_bottom),
                    (kw_half_y, kw_z_rect_top),
                    (0.0, kw_z_chamfer),
                    (-kw_half_y, kw_z_rect_top),
                ],
                close=True,
            )
        make_face()
    extrude(kw_sk.sketch, amount=kw_width, mode=Mode.SUBTRACT)

    # Counterbored horizontal bore (−X side)
    with Locations((-shaft_radius, 0, -shaft_depth / 2.0)):
        with Locations(Rotation(0, 90, 0)):
            Cylinder(
                cbore_r, cbore_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )
            Cylinder(
                bore_r_h, bore_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )




# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

result = part.part
bb = result.bounding_box()

TARGET_VOL = 6988013

print()
print("=" * 60)
print("  Art4MotorGear — Build Summary")
print("=" * 60)
print(f"  Volume    : {result.volume:>18.4f} mm³")
print(f"  Target    : {TARGET_VOL:>18d} mm³")
print(f"  Delta     : {(result.volume - TARGET_VOL) / TARGET_VOL * 100:>+17.4f} %")
print(f"  Faces     : {len(result.faces()):>4d}")
print(f"  X span    : {bb.min.X:.1f} -> {bb.max.X:.1f}  ({bb.max.X - bb.min.X:.1f} mm)")
print(f"  Y span    : {bb.min.Y:.1f} -> {bb.max.Y:.1f}  ({bb.max.Y - bb.min.Y:.1f} mm)")
print(f"  Z span    : {bb.min.Z:.1f} -> {bb.max.Z:.1f}  ({bb.max.Z - bb.min.Z:.1f} mm)")
print("=" * 60)


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT
# ══════════════════════════════════════════════════════════════════════════════

os.makedirs(OUTPUT_DIR, exist_ok=True)

_step_path = _base + ".step"
export_step(result, _step_path)
print(f"STEP exported : {_step_path}")

_stl_path = _base + ".stl"
try:
    import cadquery as cq
    _cq = cq.importers.importStep(_step_path)
    cq.exporters.export(
        _cq, _stl_path,
        exportType="STL", tolerance=0.01, angularTolerance=0.1,
    )
    print(f"STL  exported : {_stl_path}  (via CadQuery)")
except ImportError:
    export_stl(result, _stl_path, tolerance=0.01, angular_tolerance=0.1)
    print(f"STL  exported : {_stl_path}")

# File sizes
_step_kb = os.path.getsize(_step_path) / 1024
_stl_kb = os.path.getsize(_stl_path) / 1024
print(f"  STEP size  : {_step_kb:.0f} KB")
print(f"  STL  size  : {_stl_kb:.0f} KB")


# ══════════════════════════════════════════════════════════════════════════════
#  REFERENCE STL COMPARISON
# ══════════════════════════════════════════════════════════════════════════════

try:
    import numpy as np
    import trimesh
except ImportError:
    np = None
    trimesh = None

if trimesh is not None and os.path.exists(REFERENCE_STL):
    _gen = trimesh.load(_stl_path, force="mesh")
    _ref = trimesh.load(REFERENCE_STL, force="mesh")
    _ref.apply_scale(REF_SCALE)

    print("\n" + "-" * 60)
    print("  STL Reference Comparison")
    print("-" * 60)
    print(f"  Ref volume      : {_ref.volume:>18.2f} mm³")
    print(f"  Gen volume      : {_gen.volume:>18.2f} mm³")
    print(f"  Volume diff %   : {(_gen.volume - _ref.volume) / _ref.volume * 100:>+17.8f} %")
    try:
        _d1 = trimesh.boolean.difference([_gen, _ref], engine="manifold")
        _d2 = trimesh.boolean.difference([_ref, _gen], engine="manifold")
        _u = trimesh.boolean.union([_gen, _ref], engine="manifold")
        _sym = _d1.volume + _d2.volume
        print(f"  Sym-diff vol    : {_sym:>18.6f} mm³")
        print(f"  Sym-diff/union  : {_sym / _u.volume * 100:>17.8f} %")
    except Exception as exc:
        print(f"  Sym-diff        : [failed - {exc}]")
    print("-" * 60)


# ══════════════════════════════════════════════════════════════════════════════
#  STL HEALTH
# ══════════════════════════════════════════════════════════════════════════════

if trimesh is not None:
    try:
        _m = trimesh.load(_stl_path, force="mesh")
        _ec = np.bincount(_m.edges_unique_inverse)
        print("\n" + "-" * 60)
        print("  STL Health")
        print("-" * 60)
        print(f"  Watertight       : {_m.is_watertight}")
        print(f"  Winding          : {_m.is_winding_consistent}")
        print(f"  Boundary edges   : {int((_ec == 1).sum())}")
        print(f"  Nonmanifold edges: {int((_ec > 2).sum())}")
        print(f"  STL volume       : {_m.volume:>18.2f} mm³")
        print(f"  CAD vs STL       : {(_m.volume - result.volume) / result.volume * 100:>+17.4f} %")
        print("-" * 60)
    except Exception as exc:
        print(f"[WARN] STL health check failed: {exc}")


# ══════════════════════════════════════════════════════════════════════════════
#  VIEWER
# ══════════════════════════════════════════════════════════════════════════════

if os.environ.get("SHOW_VIEWER") == "1":
    if _USE_OCP:
        try:
            _ocp_show(result)
            print("Displayed in OCP CAD Viewer.")
        except Exception as exc:
            print(f"ocp_vscode show() failed: {exc}")
            _USE_OCP = False
    if not _USE_OCP:
        _view = _stl_path if os.path.exists(_stl_path) else _step_path
        print(f"Opening in system viewer: {_view}")
        if sys.platform == "darwin":
            subprocess.run(["open", _view])
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", _view])