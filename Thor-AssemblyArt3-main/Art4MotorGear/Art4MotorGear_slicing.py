"""
Art4MotorGear - build123d reconstruction from slicing-1
========================================================

This version intentionally does not use the older STL reference.  The gear
outline is reconstructed from:

    Thor-stl/build123-repo-files/Art4MotorGear/slicing-1/axis_Z/*.dxf

Those slices are from the 0.1-scale original STEP, so XY and Z are scaled by 10
to rebuild the full-size part.
"""

from build123d import *
import glob
import math
import os
import re
import subprocess
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from ocp_vscode import show as _ocp_show

    _USE_OCP = True
except Exception:
    _USE_OCP = False


# =============================================================================
# PATHS / SLICE SETTINGS
# =============================================================================

OUTPUT_DIR = "/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d"
_base = os.path.join(OUTPUT_DIR, "Art4MotorGear_slicing1_parametric")
REFERENCE_STL = os.path.join(OUTPUT_DIR, "Art4MotorGear.stl")
EXPORT_STL_FROM_REFERENCE_MESH = False

SLICE_DIR = (
    "/Users/softage/Desktop/New-boston-py-files/Thor-stl/build123-repo-files/"
    "Art4MotorGear/slicing-1/axis_Z"
)
SLICE_SCALE = 10.0
GEAR_SAMPLE_COUNT = 880
GEAR_MAX_Z_STEP = 2.5
HELIX_ANGLE = 29.5341
PITCH_RADIUS = 90.0
HELIX_TWIST_PER_MM = math.tan(math.radians(HELIX_ANGLE)) / PITCH_RADIUS
PROFILE_RADIAL_OFFSET = -0.051


# =============================================================================
# PARAMETERS
# =============================================================================

# Gear dimensions are taken from slicing-1's source bbox:
# small-scale Z max 13.00184 -> full-size 130.0184.
face_width = 130.0184
bore_radius = 25.0

# Shaft
shaft_radius = 120.0
shaft_depth = 100.0

# Keyway
kw_x_min = -75.0
kw_x_max = -45.0
kw_half_y = 29.012
kw_z_bottom = -100.0
kw_z_rect_top = -28.25
kw_z_chamfer_top = -11.5
kw_chamfer_angle = 30.0

# Bores
bore_r_h = 17.0
cbore_r = 29.5
cbore_depth = 30.0
central_bore_overlap = 1.0
side_bore_depth = shaft_radius + central_bore_overlap


# =============================================================================
# SLICE PROFILE HELPERS
# =============================================================================


def _distance(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _dedupe_adjacent(points, tolerance=1e-5):
    out = []
    for point in points:
        if not out or _distance(out[-1], point) > tolerance:
            out.append(point)
    if len(out) > 1 and _distance(out[0], out[-1]) <= tolerance:
        out.pop()
    return out


def _profile_area(points):
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    ) / 2.0


def _parse_slice_z(path):
    match = re.search(r"_(-?\d+(?:\.\d+)?)mm\.dxf$", os.path.basename(path))
    if not match:
        raise ValueError(f"Could not parse slice Z from {path}")
    return float(match.group(1)) * SLICE_SCALE


def _entity_points(entity, flatten_distance=0.02):
    if entity.dxftype() == "LINE":
        return [
            (float(entity.dxf.start.x) * SLICE_SCALE, float(entity.dxf.start.y) * SLICE_SCALE),
            (float(entity.dxf.end.x) * SLICE_SCALE, float(entity.dxf.end.y) * SLICE_SCALE),
        ]

    if hasattr(entity, "flattening"):
        return [
            (float(point[0]) * SLICE_SCALE, float(point[1]) * SLICE_SCALE)
            for point in entity.flattening(flatten_distance)
        ]

    return []


def _stitch_chains(chains):
    """Join unordered DXF curve fragments into a single closed outer loop."""
    chains = [_dedupe_adjacent(chain) for chain in chains if len(chain) >= 2]
    if not chains:
        return []

    points = chains.pop(0)

    while chains:
        last = points[-1]
        best = None
        for chain_index, chain in enumerate(chains):
            forward_gap = _distance(last, chain[0])
            reverse_gap = _distance(last, chain[-1])
            gap, reverse = (
                (reverse_gap, True)
                if reverse_gap < forward_gap
                else (forward_gap, False)
            )
            if best is None or gap < best[0]:
                best = (gap, chain_index, reverse)

        gap, chain_index, reverse = best
        chain = chains.pop(chain_index)
        if reverse:
            chain.reverse()
        if gap <= 1e-5:
            chain = chain[1:]
        points.extend(chain)

    points = _dedupe_adjacent(points)
    if _profile_area(points) < 0:
        points.reverse()
    return points


def _load_outer_loop(path):
    try:
        import ezdxf
    except ImportError as exc:
        raise RuntimeError("Install ezdxf to load slicing-1 DXF profiles") from exc

    doc = ezdxf.readfile(path)
    chains = []
    for entity in doc.modelspace():
        if getattr(entity.dxf, "layer", "") != "OUTER":
            continue
        points = _entity_points(entity)
        if points:
            chains.append(points)

    loop = _stitch_chains(chains)
    if len(loop) < 3:
        raise RuntimeError(f"No usable OUTER loop found in {path}")
    return loop


def _ray_outer_radius(points, angle):
    """Return the farthest polygon hit along a ray from the origin."""
    dx = math.cos(angle)
    dy = math.sin(angle)
    best = None

    for p1, p2 in zip(points, points[1:] + points[:1]):
        sx = p2[0] - p1[0]
        sy = p2[1] - p1[1]
        det = sx * dy - sy * dx
        if abs(det) < 1e-9:
            continue

        u = (p1[1] * dx - p1[0] * dy) / det
        radius = (p1[0] * sy - p1[1] * sx) / det
        if -1e-6 <= u <= 1.0 + 1e-6 and radius > 0:
            best = radius if best is None else max(best, radius)

    return best


def _polar_resample(points, sample_count=GEAR_SAMPLE_COUNT):
    radii = []
    fallback_radius = max(math.hypot(x, y) for x, y in points)

    for index in range(sample_count):
        angle = 2.0 * math.pi * index / sample_count
        radius = _ray_outer_radius(points, angle)
        radii.append(fallback_radius if radius is None else radius)

    return radii


def _shift_radii(radii, angle):
    """Sample a periodic polar-radius array at angle_i + angle."""
    count = len(radii)
    shift = angle / (2.0 * math.pi) * count
    shifted = []

    for index in range(count):
        source = (index + shift) % count
        low = int(math.floor(source))
        high = (low + 1) % count
        t = source - low
        shifted.append(radii[low] * (1.0 - t) + radii[high] * t)

    return shifted


def _profile_points_from_radii(radii, rotation=0.0):
    count = len(radii)
    return [
        (
            radii[index] * math.cos(2.0 * math.pi * index / count + rotation),
            radii[index] * math.sin(2.0 * math.pi * index / count + rotation),
        )
        for index in range(count)
    ]


def _load_gear_sections():
    positive_paths = [
        path
        for path in glob.glob(os.path.join(SLICE_DIR, "*.dxf"))
        if _parse_slice_z(path) >= -1e-6
    ]
    if not positive_paths:
        raise RuntimeError(f"No gear sections found in {SLICE_DIR}")

    # Use the real top outline from slicing-1 as the smooth transverse tooth
    # shape. Do not loft through every noisy Z slice directly: that creates
    # visible stacked bands on the tooth sides.
    top_path = max(positive_paths, key=_parse_slice_z)
    top_z = _parse_slice_z(top_path)
    top_radii = [
        radius + PROFILE_RADIAL_OFFSET
        for radius in _polar_resample(_load_outer_loop(top_path))
    ]

    section_count = int(math.ceil(face_width / GEAR_MAX_Z_STEP)) + 1
    return [
        (
            face_width * index / (section_count - 1),
            top_radii,
            HELIX_TWIST_PER_MM * (top_z - face_width * index / (section_count - 1)),
        )
        for index in range(section_count)
    ]


gear_sections = _load_gear_sections()


# =============================================================================
# BUILD
# =============================================================================

with BuildPart() as part:
    # 1. Gear body from slicing-1 sections.
    sketches = []
    for z, radii, rotation in gear_sections:
        with BuildSketch(Plane.XY.offset(z)) as sk:
            with BuildLine():
                Polyline(_profile_points_from_radii(radii, rotation), close=True)
            make_face()
        sketches.append(sk.sketch)

    loft(sketches, ruled=True)

    # 2. Shaft section (Z = 0 to -100).
    with Locations((0, 0, -shaft_depth)):
        Cylinder(
            shaft_radius,
            shaft_depth,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # 3. Central bore (full height).
    with Locations((0, 0, -shaft_depth)):
        Cylinder(
            bore_radius,
            shaft_depth + face_width + 1.0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )

    # 4. Keyway slot with tapered upper chamfer.
    _kw_wx = kw_x_max - kw_x_min
    with BuildSketch(Plane.YZ.offset(kw_x_min)) as kw_sk:
        with BuildLine():
            Polyline(
                [
                    (-kw_half_y, kw_z_bottom),
                    (kw_half_y, kw_z_bottom),
                    (kw_half_y, kw_z_rect_top),
                    (0.0, kw_z_chamfer_top),
                    (-kw_half_y, kw_z_rect_top),
                ],
                close=True,
            )
        make_face()
    extrude(kw_sk.sketch, amount=_kw_wx, mode=Mode.SUBTRACT)

    # 5. Horizontal counterbored bore (-X side).
    with Locations((-shaft_radius, 0, -shaft_depth / 2.0)):
        with Locations(Rotation(0, 90, 0)):
            Cylinder(
                cbore_r,
                cbore_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )
            Cylinder(
                bore_r_h,
                side_bore_depth,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )


# =============================================================================
# VALIDATION
# =============================================================================

result = part.part
bb = result.bounding_box()

print("=" * 60)
print("  Art4MotorGear - slicing-1 build summary")
print("=" * 60)
print(f"  Slice dir : {SLICE_DIR}")
print(f"  Sections  : {len(gear_sections):>4d}   samples/section: {GEAR_SAMPLE_COUNT}")
print(f"  Volume    : {result.volume:>18.4f} mm3")
print(f"  Faces     : {len(result.faces()):>4d}")
print(f"  X span    : {bb.min.X:.1f} -> {bb.max.X:.1f}  ({bb.max.X - bb.min.X:.1f} mm)")
print(f"  Y span    : {bb.min.Y:.1f} -> {bb.max.Y:.1f}  ({bb.max.Y - bb.min.Y:.1f} mm)")
print(f"  Z span    : {bb.min.Z:.1f} -> {bb.max.Z:.1f}  ({bb.max.Z - bb.min.Z:.1f} mm)")
print("=" * 60)


# =============================================================================
# EXPORT
# =============================================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

_step_path = _base + ".step"
export_step(result, _step_path)
print(f"STEP exported : {_step_path}")

_stl_path = _base + ".stl"
if EXPORT_STL_FROM_REFERENCE_MESH and os.path.exists(REFERENCE_STL):
    try:
        import trimesh

        _ref_mesh = trimesh.load(REFERENCE_STL, force="mesh")
        _ref_mesh.apply_scale(SLICE_SCALE)
        _ref_mesh.export(_stl_path)
        print(f"STL  exported : {_stl_path}  (scaled exact reference mesh)")
    except ImportError:
        print("[WARN] trimesh not installed; falling back to CAD STL export")
        EXPORT_STL_FROM_REFERENCE_MESH = False

if not EXPORT_STL_FROM_REFERENCE_MESH:
    try:
        import cadquery as cq

        _cq = cq.importers.importStep(_step_path)
        cq.exporters.export(
            _cq,
            _stl_path,
            exportType="STL",
            tolerance=0.01,
            angularTolerance=0.1,
        )
        print(f"STL  exported : {_stl_path}  (via CadQuery)")
    except ImportError:
        export_stl(result, _stl_path, tolerance=0.01, angular_tolerance=0.1)
        print(f"STL  exported : {_stl_path}")

try:
    import numpy as np
    import trimesh
except ImportError:
    np = None
    trimesh = None

if trimesh is not None and os.path.exists(REFERENCE_STL):
    _gen_mesh = trimesh.load(_stl_path, force="mesh")
    _ref_mesh = trimesh.load(REFERENCE_STL, force="mesh")
    _ref_mesh.apply_scale(SLICE_SCALE)

    print("\n" + "-" * 60)
    print("  STL Reference Comparison")
    print("-" * 60)
    print(f"  Ref volume      : {_ref_mesh.volume:>18.2f} mm3")
    print(f"  Gen volume      : {_gen_mesh.volume:>18.2f} mm3")
    print(f"  Volume diff     : {_gen_mesh.volume - _ref_mesh.volume:>+18.6f} mm3")
    print(
        f"  Volume diff %   : {(_gen_mesh.volume - _ref_mesh.volume) / _ref_mesh.volume * 100.0:>+17.8f} %"
    )

    try:
        _d1 = trimesh.boolean.difference([_gen_mesh, _ref_mesh], engine="manifold")
        _d2 = trimesh.boolean.difference([_ref_mesh, _gen_mesh], engine="manifold")
        _union = trimesh.boolean.union([_gen_mesh, _ref_mesh], engine="manifold")
        _sym = _d1.volume + _d2.volume
        print(f"  Sym-diff volume : {_sym:>18.6f} mm3")
        print(f"  Sym-diff union %: {_sym / _union.volume * 100.0:>17.8f} %")
    except Exception as exc:
        print(f"  Sym-diff        : [failed - {exc}]")
    print("-" * 60)

try:
    import cadquery as cq

    _mesh = trimesh.load(_stl_path, force="mesh")
    _edge_counts = np.bincount(_mesh.edges_unique_inverse)
    print("\n" + "-" * 60)
    print("  STL Health")
    print("-" * 60)
    print(f"  Watertight       : {_mesh.is_watertight}")
    print(f"  Winding          : {_mesh.is_winding_consistent}")
    print(f"  Boundary edges   : {int((_edge_counts == 1).sum())}")
    print(f"  Nonmanifold edges: {int((_edge_counts > 2).sum())}")
    print(f"  STL volume       : {_mesh.volume:>18.2f} mm3")
    print(f"  CAD vs STL       : {(_mesh.volume - result.volume) / result.volume * 100.0:>+17.4f} %")
    print("-" * 60)
except ImportError:
    print("[SKIP] STL health check needs trimesh and numpy")
except Exception as exc:
    print(f"[WARN] STL health check failed: {exc}")


# =============================================================================
# OPTIONAL VIEWER
# =============================================================================

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
