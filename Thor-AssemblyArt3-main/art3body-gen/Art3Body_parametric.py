"""
Parametric build123d reconstruction of Art3Body.

The model is built as editable analytic geometry rather than by importing the
reference mesh. The main shell is a capsule-column body with a lofted oblate
dome and a separately lofted internal roof void. Secondary details are layered
on with additive pads and subtractive cutters: back mounting features, inner
wall pads, side panel slots, dome vents, front holes, underside pockets, and
the stepped holes in the circular base flange.

Running this file exports STEP/STL files and validates the generated STL
against the supplied Art3Body.stl reference, including volume, scaled volume,
surface-distance, and symmetric-difference reports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from build123d import (
    Align,
    Cylinder,
    Edge,
    Mode,
    Plane,
    Solid,
    Wire,
    add,
    export_step,
    export_stl,
    BuildPart,
)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path("/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d")
OUTPUT_BASENAME = "Art3Body_main_dome_parametric"
REFERENCE_STL = OUTPUT_DIR / "Art3Body.stl"
VALIDATION_SAMPLE_COUNT = 50_000


# ---------------------------------------------------------------------------
# Scale
# ---------------------------------------------------------------------------

# The supplied face STEP is in 10x coordinates compared with Art3Body.stl.
# Keep SCALE=1.0 to overlay the STEP file. Use SCALE=0.1 to match the STL.
SCALE = 1.0


def mm(value: float) -> float:
    return value * SCALE


# ---------------------------------------------------------------------------
# Parameters from the reference STEP outer faces
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Art3BodyParams:
    # Circular base flange
    base_radius: float = mm(550.5)
    base_height: float = mm(210.0)
    base_stepped_holes_enabled: bool = True
    base_stepped_hole_centers: tuple[tuple[float, float], ...] = (
        (mm(225.0), mm(390.0)),
        (mm(-225.0), mm(390.0)),
        (mm(225.0), mm(-390.0)),
        (mm(-225.0), mm(-390.0)),
    )
    base_stepped_hole_radius: float = mm(17.0)
    base_stepped_hole_start_z: float = mm(70.0)
    base_stepped_hole_step_z: float = mm(180.0)
    base_stepped_hole_end_z: float = mm(210.0)
    base_stepped_hole_counterbore_radius: float = mm(29.5)

    # Capsule body footprint. The straight section spans X=-200..200 and the
    # two rounded sides have radius 350, giving total X width 1100 and Y width 700.
    capsule_half_straight: float = mm(200.0)
    capsule_radius: float = mm(350.0)
    # Keep loft end sections just inside the analytic capsule limit to avoid
    # zero-area STL triangles at the front/back dome seams.
    capsule_loft_end_fraction: float = 0.999
    body_bottom_z: float = mm(210.0)

    # Outer dome is an oblate spheroid (ellipsoid with a=c), centered on the
    # capsule centerline. Each Y-slice is a circular arc in XZ with the same
    # center Z and radius r(Y) = dome_arc_radius_xz * sqrt(1 - (Y/dome_arc_radius_y)^2).
    # Derived from the reference slices in build123-repo-files/Art3Body/slicing.
    dome_arc_center_z: float = mm(865.0)
    dome_arc_radius_xz: float = mm(660.0)
    dome_arc_radius_y: float = mm(533.74)

    # Three long vent slots projected through the upper-right dome surface.
    top_dome_slots_enabled: bool = True
    top_dome_slot_start_x: float = mm(100.0)
    top_dome_slot_end_x: float = mm(420.0)
    top_dome_slot_centers_y: tuple[float, ...] = (mm(-100.0), mm(0.0), mm(100.0))
    top_dome_slot_radius: float = mm(10.0)
    top_dome_slot_cut_z_min: float = mm(1225.0)
    top_dome_slot_cut_z_max: float = mm(1600.0)

    # Optional lower/base shaping.
    include_base_recess: bool = True
    base_recess_radius: float = mm(502.0)
    base_recess_depth: float = mm(70.0)

    # Second-stage underside pocket: R405 circle plus a rectangular back tab,
    # cut upward from the first bottom recess floor to Z=130.
    bottom_profile_cut_enabled: bool = True
    bottom_profile_cut_radius: float = mm(405.0)
    bottom_profile_cut_start_z: float = mm(70.0)
    bottom_profile_cut_end_z: float = mm(130.0)
    bottom_profile_rect_half_width: float = mm(50.0)
    bottom_profile_rect_back_y: float = mm(470.0)

    # Hollow interior. The straight section remains X=-200..200, but the bore
    # radius is 300, leaving the 50 mm nominal side wall visible in the STEP.
    shell_enabled: bool = True
    inner_capsule_half_straight: float = mm(200.0)
    inner_capsule_radius: float = mm(300.0)
    inner_capsule_loft_end_fraction: float = 0.999
    inner_bottom_z: float = mm(70.0)

    # Inner dome is a second oblate spheroid, concentric-offset from the outer.
    # Reference slices show r_inner(Y) ~= r_outer(Y) - 50 at every Y, and the
    # inner arc center sits 65 mm below the outer arc center.
    inner_dome_arc_center_z: float = mm(800.0)
    inner_dome_arc_radius_xz: float = mm(610.0)
    inner_dome_arc_radius_y: float = mm(525.0)

    # Back-side circular mounting geometry, located on the +Y face.
    back_features_enabled: bool = True
    back_face_y: float = mm(350.0)
    back_feature_center_x: float = mm(0.0)
    back_feature_center_z: float = mm(885.0)

    # Shallow conical pad visible as the large tapered circular land.
    back_pad_depth: float = mm(60.0)
    back_pad_base_radius: float = mm(180.0)
    back_pad_top_radius: float = mm(120.0)

    # Central recess/counterbore and through bore.
    back_boss_inner_y: float = mm(320.0)
    back_boss_outer_y: float = mm(410.0)
    back_body_counterbore_radius: float = mm(82.0)
    back_body_counterbore_depth: float = mm(90.0)
    back_bore_radius: float = mm(50.0)
    # Through-hole cutters start inside the hollow so their inner caps do not remain.
    back_bore_start_y: float = mm(280.0)
    back_bore_end_y: float = mm(425.0)

    # U-shaped/arched relief around the boss.
    back_arch_outer_radius: float = mm(280.0)
    back_arch_inner_radius: float = mm(200.0)
    back_arch_end_fillet_radius: float = mm(40.0)
    # Starts inside the hollow cavity so no thin cap/layer remains on the inner wall.
    back_arch_start_y: float = mm(280.0)
    back_arch_end_y: float = mm(356.0)

    # Vertical rectangular recess through the boss. The original feature is a
    # continuous slot, not two isolated top/bottom pockets.
    back_tab_width: float = mm(69.0)
    back_tab_y_start: float = mm(370.0)
    back_tab_y_end: float = mm(410.0)
    back_lower_tab_z_min: float = mm(725.0)
    back_lower_tab_z_max: float = mm(810.611)
    back_upper_tab_z_min: float = mm(959.389)
    back_upper_tab_z_max: float = mm(1045.0)
    back_rect_hole_radius: float = mm(17.0)
    back_rect_hole_spotface_radius: float = mm(33.5)
    back_rect_hole_spotface_start_y: float = mm(300.0)
    back_rect_hole_spotface_end_y: float = mm(330.0)
    back_lower_rect_hole_z: float = mm(775.0)
    back_upper_rect_hole_z: float = mm(995.0)
    back_lower_rect_spotface_z_min: float = mm(741.5)
    back_lower_rect_spotface_z_max: float = mm(804.012)
    back_upper_rect_spotface_z_min: float = mm(965.988)
    back_upper_rect_spotface_z_max: float = mm(1028.5)

    # Small side holes flanking the main circular boss.
    back_side_hole_x: float = mm(250.0)
    back_side_hole_z: float = mm(850.0)
    back_side_hole_radius: float = mm(17.0)
    back_side_hex_radius: float = mm(33.5)
    back_side_hex_start_y: float = mm(280.0)
    back_side_hex_end_y: float = mm(330.0)

    # Front-side through holes on the -Y face.
    front_holes_enabled: bool = True
    front_hole_start_y: float = mm(-360.0)
    front_hole_end_y: float = mm(-240.0)
    front_small_hole_radius: float = mm(17.0)
    front_large_hole_radius: float = mm(50.0)
    front_small_hole_centers: tuple[tuple[float, float], ...] = (
        (mm(-160.0), mm(755.0)),
        (mm(160.0), mm(755.0)),
        (mm(0.0), mm(1065.0)),
    )
    front_large_hole_center: tuple[float, float] = (mm(0.0), mm(885.0))

    # Raised wedge pads on the inside of the -Y/front wall around the R17 holes.
    front_inner_pads_enabled: bool = True
    front_inner_pad_wall_y: float = mm(-305.0)
    front_inner_pad_inner_y: float = mm(-250.0)
    front_inner_pad_half_width: float = mm(50.0)
    front_inner_pad_bottom_offset: float = mm(-60.0)
    front_inner_pad_wall_top_offset: float = mm(85.0)
    front_inner_pad_inner_top_offset: float = mm(30.0)
    front_inner_pad_notch_end_y: float = mm(-270.0)
    front_inner_pad_notch_radius: float = mm(33.5)

    # Raised bracket pad on the left internal curved wall.
    left_inner_side_pad_enabled: bool = True
    left_inner_side_pad_wall_x: float = mm(-505.0)
    left_inner_side_pad_visible_wall_x: float = mm(-500.0)
    left_inner_side_pad_inner_x: float = mm(-400.0)
    left_inner_side_pad_half_width_y: float = mm(75.0)
    left_inner_side_pad_bottom_z: float = mm(290.0)
    left_inner_side_pad_wall_top_z: float = mm(460.0)
    left_inner_side_pad_inner_top_z: float = mm(355.0)
    left_inner_side_pad_lower_notch_half_width_y: float = mm(56.0)
    left_inner_side_pad_lower_notch_top_z: float = mm(305.0)
    left_inner_side_pad_slot_half_width_y: float = mm(29.012)
    left_inner_side_pad_slot_tip_x: float = mm(-497.5)
    left_inner_side_pad_slot_shoulder_x: float = mm(-480.75)
    left_inner_side_pad_slot_bottom_z: float = mm(323.5)
    left_inner_side_pad_slot_top_z: float = mm(353.5)
    left_inner_side_pad_hole_x: float = mm(-464.0)
    left_inner_side_pad_hole_y: float = mm(0.0)
    left_inner_side_pad_hole_radius: float = mm(17.0)
    left_inner_side_pad_hole_start_z: float = mm(280.0)
    left_inner_side_pad_hole_end_z: float = mm(465.0)

    # Upper flat panel with vent slots on the left internal curved wall.
    left_upper_recess_enabled: bool = True
    left_upper_recess_wall_x: float = mm(-500.0)
    left_upper_recess_face_x: float = mm(-460.0)
    left_upper_cut_outer_x: float = mm(-550.0)
    left_upper_cut_inner_x: float = mm(-420.0)
    left_upper_recess_half_width_y: float = mm(200.0)
    left_upper_recess_bottom_z: float = mm(860.0)
    left_upper_recess_top_z: float = mm(1260.0)
    left_upper_slot_centers_y: tuple[float, ...] = (
        mm(-105.0),
        mm(-35.0),
        mm(35.0),
        mm(105.0),
    )
    left_upper_slot_radius: float = mm(10.0)
    left_upper_slot_bottom_center_z: float = mm(940.0)
    left_upper_slot_top_center_z: float = mm(1180.0)
    left_upper_hole_centers: tuple[tuple[float, float], ...] = (
        (mm(-160.0), mm(900.0)),
        (mm(160.0), mm(900.0)),
        (mm(-160.0), mm(1220.0)),
        (mm(160.0), mm(1220.0)),
    )
    left_upper_hole_radius: float = mm(17.0)
    left_upper_hole_pocket_radius: float = mm(29.5)
    left_upper_hole_pocket_inner_x: float = mm(-480.0)
    left_upper_panel_square_cut_enabled: bool = True
    left_upper_panel_square_cut_size: float = mm(400.0)
    left_upper_panel_square_cut_depth: float = mm(150.0)

    # Opposite curved-wall profile with chamfered side returns and lower holes.
    right_profile_enabled: bool = True
    right_profile_inner_clear_x: float = mm(300.0)
    right_profile_face_x: float = mm(490.0)
    right_profile_chamfer_x: float = mm(460.0)
    right_profile_outer_x: float = mm(550.0)
    right_profile_face_half_width_y: float = mm(182.5)
    right_profile_outer_half_width_y: float = mm(212.5)
    right_profile_bottom_z: float = mm(786.0)
    right_profile_top_z: float = mm(1236.0)
    right_profile_hole_centers_y: tuple[float, ...] = (mm(-45.0), mm(45.0))
    right_profile_hole_z: float = mm(846.0)
    right_profile_hole_radius: float = mm(17.0)
    right_profile_counterbore_radius: float = mm(29.5)
    right_profile_counterbore_start_x: float = mm(510.0)

P = Art3BodyParams()


# ---------------------------------------------------------------------------
# Dome/body section helpers
# ---------------------------------------------------------------------------


def capsule_x_half_width(y: float, p: Art3BodyParams = P) -> float:
    """Half width of the capsule footprint at a given Y station."""
    y_abs = min(abs(y), p.capsule_radius)
    return p.capsule_half_straight + math.sqrt(max(p.capsule_radius**2 - y_abs**2, 0.0))


def inner_capsule_x_half_width(y: float, p: Art3BodyParams = P) -> float:
    """Half width of the internal capsule bore at a given Y station."""
    y_abs = min(abs(y), p.inner_capsule_radius)
    return p.inner_capsule_half_straight + math.sqrt(
        max(p.inner_capsule_radius**2 - y_abs**2, 0.0)
    )


def dome_outer_radius_at_y(y: float, p: Art3BodyParams = P) -> float:
    """XZ-plane arc radius of the outer dome at a Y station (ellipsoid slice)."""
    t = min(abs(y) / p.dome_arc_radius_y, 1.0)
    return p.dome_arc_radius_xz * math.sqrt(max(1.0 - t * t, 0.0))


def dome_inner_radius_at_y(y: float, p: Art3BodyParams = P) -> float:
    """XZ-plane arc radius of the inner dome at a Y station (ellipsoid slice)."""
    t = min(abs(y) / p.inner_dome_arc_radius_y, 1.0)
    return p.inner_dome_arc_radius_xz * math.sqrt(max(1.0 - t * t, 0.0))


def side_seam_z(y: float, p: Art3BodyParams = P) -> float:
    """Height of the left/right side seam where the dome arc meets the wall."""
    half = capsule_x_half_width(y, p)
    r = dome_outer_radius_at_y(y, p)
    return p.dome_arc_center_z + math.sqrt(max(r * r - half * half, 0.0))


def inner_side_seam_z(y: float, p: Art3BodyParams = P) -> float:
    """Height of the internal side seam where the bore meets the roof arc."""
    half = inner_capsule_x_half_width(y, p)
    r = dome_inner_radius_at_y(y, p)
    return p.inner_dome_arc_center_z + math.sqrt(max(r * r - half * half, 0.0))


def crown_z_at_y(y: float, p: Art3BodyParams = P) -> float:
    """Dome crown height for a Y section."""
    return p.dome_arc_center_z + dome_outer_radius_at_y(y, p)


def inner_crown_z_at_y(y: float, p: Art3BodyParams = P) -> float:
    """Internal roof crown height for a Y section."""
    return p.inner_dome_arc_center_z + dome_inner_radius_at_y(y, p)


def y_stations(p: Art3BodyParams = P) -> list[float]:
    """Symmetric Y stations with extra sections near the sharper front/back ends."""
    r = p.capsule_radius
    fractions = [0.0, 0.14, 0.28, 0.42, 0.57, 0.72, 0.84, 0.93, p.capsule_loft_end_fraction]
    positive = [r * f for f in fractions]
    return [-v for v in reversed(positive[1:])] + positive


def inner_y_stations(p: Art3BodyParams = P) -> list[float]:
    """Symmetric Y stations for the internal bore and roof underside."""
    r = p.inner_capsule_radius
    fractions = [
        0.0,
        0.14,
        0.28,
        0.42,
        0.57,
        0.72,
        0.84,
        0.93,
        p.inner_capsule_loft_end_fraction,
    ]
    positive = [r * f for f in fractions]
    return [-v for v in reversed(positive[1:])] + positive


def make_body_dome_section(y: float, p: Art3BodyParams = P) -> Wire:
    """Closed XZ wire at a fixed Y station, with a circular arc dome top."""
    half_width = capsule_x_half_width(y, p)
    x_left = -half_width
    x_right = half_width
    z_wall_top = side_seam_z(y, p)
    z_crown = crown_z_at_y(y, p)

    left = (x_left, y, z_wall_top)
    apex = (0.0, y, z_crown)
    right = (x_right, y, z_wall_top)
    bottom_right = (x_right, y, p.body_bottom_z)
    bottom_left = (x_left, y, p.body_bottom_z)

    edges = [
        Edge.make_three_point_arc(left, apex, right),
        Edge.make_line(right, bottom_right),
        Edge.make_line(bottom_right, bottom_left),
        Edge.make_line(bottom_left, left),
    ]
    return Wire(edges, sequenced=True)


def make_inner_void_section(y: float, p: Art3BodyParams = P) -> Wire:
    """Closed XZ wire for the internal bore, with a circular arc roof."""
    half_width = inner_capsule_x_half_width(y, p)
    x_left = -half_width
    x_right = half_width
    z_wall_top = inner_side_seam_z(y, p)
    z_crown = inner_crown_z_at_y(y, p)

    left = (x_left, y, z_wall_top)
    apex = (0.0, y, z_crown)
    right = (x_right, y, z_wall_top)
    bottom_right = (x_right, y, p.inner_bottom_z)
    bottom_left = (x_left, y, p.inner_bottom_z)

    edges = [
        Edge.make_three_point_arc(left, apex, right),
        Edge.make_line(right, bottom_right),
        Edge.make_line(bottom_right, bottom_left),
        Edge.make_line(bottom_left, left),
    ]
    return Wire(edges, sequenced=True)


def build_main_body_and_dome(p: Art3BodyParams = P) -> Solid:
    """Build the capsule body and dome as one continuous lofted solid."""
    sections = [make_body_dome_section(y, p) for y in y_stations(p)]
    return Solid.make_loft(sections, ruled=False)


def build_inner_void(p: Art3BodyParams = P) -> Solid:
    """Build the main internal hollow as a subtractive solid."""
    sections = [make_inner_void_section(y, p) for y in inner_y_stations(p)]
    return Solid.make_loft(sections, ruled=False)


def y_axis_plane(x: float, y: float, z: float) -> Plane:
    """Plane whose local Z axis points along global +Y."""
    return Plane((x, y, z), (1, 0, 0), (0, 1, 0))


def y_axis_cylinder(x: float, y_start: float, z: float, radius: float, depth: float) -> Solid:
    """Cylinder with its axis along global +Y."""
    return Solid.make_cylinder(radius, depth, plane=y_axis_plane(x, y_start, z))


def y_axis_cone(
    x: float,
    y_start: float,
    z: float,
    base_radius: float,
    top_radius: float,
    depth: float,
) -> Solid:
    """Cone/frustum with its axis along global +Y."""
    return Solid.make_cone(base_radius, top_radius, depth, plane=y_axis_plane(x, y_start, z))


def z_axis_plane(x: float, y: float, z: float) -> Plane:
    """Plane whose local Z axis points along global +Z."""
    return Plane((x, y, z), (1, 0, 0), (0, 0, 1))


def z_axis_cylinder(x: float, y: float, z_start: float, radius: float, depth: float) -> Solid:
    """Cylinder with its axis along global +Z."""
    return Solid.make_cylinder(radius, depth, plane=z_axis_plane(x, y, z_start))


def x_axis_plane(x: float, y: float, z: float) -> Plane:
    """Plane whose local Z axis points along global +X."""
    return Plane((x, y, z), (0, 1, 0), (1, 0, 0))


def x_axis_cylinder(x_start: float, y: float, z: float, radius: float, depth: float) -> Solid:
    """Cylinder with its axis along global +X."""
    return Solid.make_cylinder(radius, depth, plane=x_axis_plane(x_start, y, z))


def z_axis_box(
    x_min: float,
    y_min: float,
    z_min: float,
    x_max: float,
    y_max: float,
    z_max: float,
) -> Solid:
    """Box specified in global min/max coordinates."""
    return Solid.make_box(
        x_max - x_min,
        y_max - y_min,
        z_max - z_min,
        plane=z_axis_plane(x_min, y_min, z_min),
    )


def y_axis_box(
    x_min: float,
    y_min: float,
    z_min: float,
    x_max: float,
    y_max: float,
    z_max: float,
) -> Solid:
    """Box specified in global min/max coordinates."""
    return Solid.make_box(
        x_max - x_min,
        z_max - z_min,
        y_max - y_min,
        plane=y_axis_plane(x_min, y_min, z_max),
    )


def x_axis_capsule_slot(
    x_start: float,
    x_end: float,
    y_center: float,
    z_bottom_center: float,
    z_top_center: float,
    radius: float,
) -> Solid:
    """Rounded vertical slot in the YZ plane, extruded along X."""

    def slot_wire(x: float) -> Wire:
        lower_left = (x, y_center - radius, z_bottom_center)
        upper_left = (x, y_center - radius, z_top_center)
        top_mid = (x, y_center, z_top_center + radius)
        upper_right = (x, y_center + radius, z_top_center)
        lower_right = (x, y_center + radius, z_bottom_center)
        bottom_mid = (x, y_center, z_bottom_center - radius)
        edges = [
            Edge.make_line(lower_left, upper_left),
            Edge.make_three_point_arc(upper_left, top_mid, upper_right),
            Edge.make_line(upper_right, lower_right),
            Edge.make_three_point_arc(lower_right, bottom_mid, lower_left),
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft([slot_wire(x_start), slot_wire(x_end)], ruled=True)


def z_axis_capsule_slot(
    x_start: float,
    x_end: float,
    y_center: float,
    z_min: float,
    z_max: float,
    radius: float,
) -> Solid:
    """Rounded horizontal slot in the XY plane, extruded along Z."""

    def slot_wire(z: float) -> Wire:
        left_top = (x_start, y_center + radius, z)
        left_mid = (x_start - radius, y_center, z)
        right_top = (x_end, y_center + radius, z)
        right_mid = (x_end + radius, y_center, z)
        right_bottom = (x_end, y_center - radius, z)
        left_bottom = (x_start, y_center - radius, z)
        edges = [
            Edge.make_three_point_arc(left_bottom, left_mid, left_top),
            Edge.make_line(left_top, right_top),
            Edge.make_three_point_arc(right_top, right_mid, right_bottom),
            Edge.make_line(right_bottom, left_bottom),
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft([slot_wire(z_min), slot_wire(z_max)], ruled=True)


def z_axis_polygon_prism(points_xy: list[tuple[float, float]], z_min: float, z_max: float) -> Solid:
    """Prism from a closed XY polygon between two Z stations."""

    def section(z: float) -> Wire:
        points = [(x, y, z) for x, y in points_xy]
        edges = [
            Edge.make_line(points[i], points[(i + 1) % len(points)])
            for i in range(len(points))
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft([section(z_min), section(z_max)], ruled=True)


def make_left_upper_panel(p: Art3BodyParams = P) -> Solid:
    """Upper side panel clipped to the original outer shell envelope."""
    raw_panel = z_axis_box(
        p.left_upper_recess_wall_x,
        -p.left_upper_recess_half_width_y,
        p.left_upper_recess_bottom_z,
        p.left_upper_recess_face_x,
        p.left_upper_recess_half_width_y,
        p.left_upper_recess_top_z,
    )
    return raw_panel.intersect(build_main_body_and_dome(p))


def make_right_profile_material(p: Art3BodyParams = P) -> Solid:
    """Right curved-wall profile volume clipped to the main shell."""
    h_face = p.right_profile_face_half_width_y
    h_outer = p.right_profile_outer_half_width_y
    points = [
        (p.right_profile_face_x, -h_face),
        (p.right_profile_chamfer_x, -h_outer),
        (p.right_profile_outer_x, -h_outer),
        (p.right_profile_outer_x, h_outer),
        (p.right_profile_chamfer_x, h_outer),
        (p.right_profile_face_x, h_face),
    ]
    raw_profile = z_axis_polygon_prism(
        points,
        p.right_profile_bottom_z,
        p.right_profile_top_z,
    )
    return raw_profile.intersect(build_main_body_and_dome(p))


def make_right_profile_clearance(p: Art3BodyParams = P) -> Solid:
    """Cut away the inside of the right profile to expose the flat/chamfered face."""
    h_face = p.right_profile_face_half_width_y
    h_outer = p.right_profile_outer_half_width_y
    points = [
        (p.right_profile_inner_clear_x, -h_outer),
        (p.right_profile_chamfer_x, -h_outer),
        (p.right_profile_face_x, -h_face),
        (p.right_profile_face_x, h_face),
        (p.right_profile_chamfer_x, h_outer),
        (p.right_profile_inner_clear_x, h_outer),
    ]
    return z_axis_polygon_prism(points, p.right_profile_bottom_z, p.right_profile_top_z)


def add_bottom_profile_cut(p: Art3BodyParams = P) -> None:
    """Add the deeper R405 + rear-rectangle underside pocket."""
    depth = p.bottom_profile_cut_end_z - p.bottom_profile_cut_start_z
    rect_y_min = math.sqrt(
        max(p.bottom_profile_cut_radius**2 - p.bottom_profile_rect_half_width**2, 0.0)
    )

    add(
        z_axis_cylinder(
            0.0,
            0.0,
            p.bottom_profile_cut_start_z,
            p.bottom_profile_cut_radius,
            depth,
        ),
        mode=Mode.SUBTRACT,
    )
    add(
        z_axis_box(
            -p.bottom_profile_rect_half_width,
            rect_y_min,
            p.bottom_profile_cut_start_z,
            p.bottom_profile_rect_half_width,
            p.bottom_profile_rect_back_y,
            p.bottom_profile_cut_end_z,
        ),
        mode=Mode.SUBTRACT,
    )


def add_base_stepped_holes(p: Art3BodyParams = P) -> None:
    """Add the four stepped through holes in the circular base flange."""
    through_depth = p.base_stepped_hole_end_z - p.base_stepped_hole_start_z
    counterbore_depth = p.base_stepped_hole_end_z - p.base_stepped_hole_step_z
    for x, y in p.base_stepped_hole_centers:
        add(
            z_axis_cylinder(
                x,
                y,
                p.base_stepped_hole_start_z,
                p.base_stepped_hole_radius,
                through_depth,
            ),
            mode=Mode.SUBTRACT,
        )
        add(
            z_axis_cylinder(
                x,
                y,
                p.base_stepped_hole_step_z,
                p.base_stepped_hole_counterbore_radius,
                counterbore_depth,
            ),
            mode=Mode.SUBTRACT,
        )


def clipped_y_axis_cylinder(
    x: float,
    y_start: float,
    z: float,
    radius: float,
    depth: float,
    z_min: float,
    z_max: float,
) -> Solid:
    """Y-axis cylinder clipped to a global Z window."""
    cylinder = y_axis_cylinder(x, y_start, z, radius, depth)
    clip_box = y_axis_box(x - radius, y_start, z_min, x + radius, y_start + depth, z_max)
    return cylinder.intersect(clip_box)


def y_axis_hex_prism(
    x: float,
    y_start: float,
    z: float,
    radius: float,
    depth: float,
) -> Solid:
    """Hexagonal prism with point-to-point width along X and axis along +Y."""

    def hex_wire(y: float) -> Wire:
        points = []
        for angle_deg in [0, 60, 120, 180, 240, 300]:
            angle = math.radians(angle_deg)
            points.append((x + radius * math.cos(angle), y, z + radius * math.sin(angle)))
        edges = [
            Edge.make_line(points[index], points[(index + 1) % len(points)])
            for index in range(len(points))
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft(
        [hex_wire(y_start), hex_wire(y_start + depth)],
        ruled=True,
    )


def make_front_inner_pad(
    x: float,
    hole_z: float,
    p: Art3BodyParams = P,
) -> Solid:
    """Raised trapezoid pad on the inner front wall, sloping down into the cavity."""

    x_min = x - p.front_inner_pad_half_width
    x_max = x + p.front_inner_pad_half_width
    z_min = hole_z + p.front_inner_pad_bottom_offset
    z_wall_top = hole_z + p.front_inner_pad_wall_top_offset
    z_inner_top = hole_z + p.front_inner_pad_inner_top_offset

    def section(y: float, z_top: float) -> Wire:
        points = [
            (x_min, y, z_min),
            (x_max, y, z_min),
            (x_max, y, z_top),
            (x_min, y, z_top),
        ]
        edges = [
            Edge.make_line(points[index], points[(index + 1) % len(points)])
            for index in range(len(points))
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft(
        [
            section(p.front_inner_pad_wall_y, z_wall_top),
            section(p.front_inner_pad_inner_y, z_inner_top),
        ],
        ruled=True,
    )


def make_front_inner_pad_notch(
    x: float,
    hole_z: float,
    p: Art3BodyParams = P,
) -> Solid:
    """Wall-side lower notch in a front inner pad with chamfered upper corners."""
    radius = p.front_inner_pad_notch_radius
    half_width = radius * math.sqrt(3.0) / 2.0
    z_min = hole_z + p.front_inner_pad_bottom_offset
    z_shoulder = hole_z + radius / 2.0
    z_peak = hole_z + radius
    y_start = p.front_inner_pad_wall_y - mm(1.0)

    def section(y: float) -> Wire:
        points = [
            (x - half_width, y, z_min),
            (x + half_width, y, z_min),
            (x + half_width, y, z_shoulder),
            (x, y, z_peak),
            (x - half_width, y, z_shoulder),
        ]
        edges = [
            Edge.make_line(points[index], points[(index + 1) % len(points)])
            for index in range(len(points))
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft(
        [
            section(y_start),
            section(p.front_inner_pad_notch_end_y),
        ],
        ruled=True,
    )


def make_left_inner_side_pad(p: Art3BodyParams = P) -> Solid:
    """Raised wedge pad on the left internal curved wall."""

    def section(x: float, z_top: float) -> Wire:
        points = [
            (x, -p.left_inner_side_pad_half_width_y, p.left_inner_side_pad_bottom_z),
            (x, p.left_inner_side_pad_half_width_y, p.left_inner_side_pad_bottom_z),
            (x, p.left_inner_side_pad_half_width_y, z_top),
            (x, -p.left_inner_side_pad_half_width_y, z_top),
        ]
        edges = [
            Edge.make_line(points[index], points[(index + 1) % len(points)])
            for index in range(len(points))
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft(
        [
            section(p.left_inner_side_pad_wall_x, p.left_inner_side_pad_wall_top_z),
            section(p.left_inner_side_pad_inner_x, p.left_inner_side_pad_inner_top_z),
        ],
        ruled=True,
    )


def make_left_inner_side_pad_slot(p: Art3BodyParams = P) -> Solid:
    """Chamfer-ended rectangular slot through the left inner side pad."""
    y = p.left_inner_side_pad_slot_half_width_y
    points_xy = [
        (p.left_inner_side_pad_inner_x, -y),
        (p.left_inner_side_pad_inner_x, y),
        (p.left_inner_side_pad_slot_shoulder_x, y),
        (p.left_inner_side_pad_slot_tip_x, 0.0),
        (p.left_inner_side_pad_slot_shoulder_x, -y),
    ]

    def section(z: float) -> Wire:
        points = [(x, y_value, z) for x, y_value in points_xy]
        edges = [
            Edge.make_line(points[index], points[(index + 1) % len(points)])
            for index in range(len(points))
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft(
        [
            section(p.left_inner_side_pad_slot_bottom_z),
            section(p.left_inner_side_pad_slot_top_z),
        ],
        ruled=True,
    )


def make_back_arch_relief(p: Art3BodyParams = P) -> Solid:
    """Semi-annular relief cut with R40 fillets contained within the original ends."""

    def arch_wire(y: float) -> Wire:
        zc = p.back_feature_center_z
        outer_r = p.back_arch_outer_radius
        inner_r = p.back_arch_inner_radius
        cap_r = p.back_arch_end_fillet_radius
        cap_center_r = (outer_r + inner_r) / 2
        cap_center_x = math.sqrt(max(cap_center_r**2 - cap_r**2, 0.0))
        cap_center_z = zc + cap_r

        outer_tx = outer_r * cap_center_x / cap_center_r
        outer_tz = zc + outer_r * cap_r / cap_center_r
        inner_tx = inner_r * cap_center_x / cap_center_r
        inner_tz = zc + inner_r * cap_r / cap_center_r

        outer_left = (-outer_tx, y, outer_tz)
        outer_top = (0.0, y, zc + outer_r)
        outer_right = (outer_tx, y, outer_tz)
        inner_right = (inner_tx, y, inner_tz)
        inner_top = (0.0, y, zc + inner_r)
        inner_left = (-inner_tx, y, inner_tz)
        right_cap_mid = (cap_center_x, y, zc)
        left_cap_mid = (-cap_center_x, y, zc)

        edges = [
            Edge.make_three_point_arc(outer_left, outer_top, outer_right),
            Edge.make_three_point_arc(outer_right, right_cap_mid, inner_right),
            Edge.make_three_point_arc(inner_right, inner_top, inner_left),
            Edge.make_three_point_arc(inner_left, left_cap_mid, outer_left),
        ]
        return Wire(edges, sequenced=True)

    return Solid.make_loft(
        [arch_wire(p.back_arch_start_y), arch_wire(p.back_arch_end_y)],
        ruled=True,
    )


def add_back_features(p: Art3BodyParams = P) -> None:
    """Add the main +Y back mounting feature set."""
    x = p.back_feature_center_x
    z = p.back_feature_center_z

    add(
        y_axis_cone(
            x,
            p.back_face_y,
            z,
            p.back_pad_base_radius,
            p.back_pad_top_radius,
            p.back_pad_depth,
        ),
        mode=Mode.ADD,
    )

    rect_x_min = x - p.back_tab_width / 2
    rect_x_max = x + p.back_tab_width / 2
    # Cut the slot before the R82 counterbore so its intersection is imprinted
    # on the cylindrical recess face, matching the small rectangular window.
    add(
        y_axis_box(
            rect_x_min,
            p.back_tab_y_start,
            p.back_lower_tab_z_min,
            rect_x_max,
            p.back_tab_y_end,
            p.back_upper_tab_z_max,
        ),
        mode=Mode.SUBTRACT,
    )

    for hole_z, z_min, z_max in [
        (
            p.back_lower_rect_hole_z,
            p.back_lower_rect_spotface_z_min,
            p.back_lower_rect_spotface_z_max,
        ),
        (
            p.back_upper_rect_hole_z,
            p.back_upper_rect_spotface_z_min,
            p.back_upper_rect_spotface_z_max,
        ),
    ]:
        add(
            clipped_y_axis_cylinder(
                x,
                p.back_rect_hole_spotface_start_y,
                hole_z,
                p.back_rect_hole_spotface_radius,
                p.back_rect_hole_spotface_end_y - p.back_rect_hole_spotface_start_y,
                z_min,
                z_max,
            ),
            mode=Mode.SUBTRACT,
        )

    add(
        y_axis_cylinder(
            x,
            p.back_boss_outer_y - p.back_body_counterbore_depth,
            z,
            p.back_body_counterbore_radius,
            p.back_body_counterbore_depth,
        ),
        mode=Mode.SUBTRACT,
    )

    add(make_back_arch_relief(p), mode=Mode.SUBTRACT)

    add(
        y_axis_cylinder(
            x,
            p.back_bore_start_y,
            z,
            p.back_bore_radius,
            p.back_bore_end_y - p.back_bore_start_y,
        ),
        mode=Mode.SUBTRACT,
    )

    for hole_z in [p.back_lower_rect_hole_z, p.back_upper_rect_hole_z]:
        add(
            y_axis_cylinder(
                x,
                p.back_bore_start_y,
                hole_z,
                p.back_rect_hole_radius,
                p.back_bore_end_y - p.back_bore_start_y,
            ),
            mode=Mode.SUBTRACT,
        )

    for side_x in [-p.back_side_hole_x, p.back_side_hole_x]:
        add(
            y_axis_hex_prism(
                side_x,
                p.back_side_hex_start_y,
                p.back_side_hole_z,
                p.back_side_hex_radius,
                p.back_side_hex_end_y - p.back_side_hex_start_y,
            ),
            mode=Mode.SUBTRACT,
        )
        add(
            y_axis_cylinder(
                side_x,
                p.back_bore_start_y,
                p.back_side_hole_z,
                p.back_side_hole_radius,
                p.back_bore_end_y - p.back_bore_start_y,
            ),
            mode=Mode.SUBTRACT,
        )


def add_front_holes(p: Art3BodyParams = P) -> None:
    """Add the main through holes on the -Y/front face."""
    depth = p.front_hole_end_y - p.front_hole_start_y
    for x, z in p.front_small_hole_centers:
        add(
            y_axis_cylinder(
                x,
                p.front_hole_start_y,
                z,
                p.front_small_hole_radius,
                depth,
            ),
            mode=Mode.SUBTRACT,
        )

    add(
        y_axis_cylinder(
            p.front_large_hole_center[0],
            p.front_hole_start_y,
            p.front_large_hole_center[1],
            p.front_large_hole_radius,
            depth,
        ),
        mode=Mode.SUBTRACT,
    )


def add_top_dome_slots(p: Art3BodyParams = P) -> None:
    """Cut the three rounded vent slots through the upper dome."""
    for y in p.top_dome_slot_centers_y:
        add(
            z_axis_capsule_slot(
                p.top_dome_slot_start_x,
                p.top_dome_slot_end_x,
                y,
                p.top_dome_slot_cut_z_min,
                p.top_dome_slot_cut_z_max,
                p.top_dome_slot_radius,
            ),
            mode=Mode.SUBTRACT,
        )


def add_front_inner_pads(p: Art3BodyParams = P) -> None:
    """Add the raised internal pads around the three front R17 holes."""
    for x, z in p.front_small_hole_centers:
        add(make_front_inner_pad(x, z, p), mode=Mode.ADD)
        add(make_front_inner_pad_notch(x, z, p), mode=Mode.SUBTRACT)


def add_left_inner_side_pad(p: Art3BodyParams = P) -> None:
    """Add the left internal side bracket pad and its local cuts."""
    add(make_left_inner_side_pad(p), mode=Mode.ADD)
    add(
        z_axis_box(
            p.left_inner_side_pad_visible_wall_x,
            -p.left_inner_side_pad_lower_notch_half_width_y,
            p.left_inner_side_pad_bottom_z,
            p.left_inner_side_pad_inner_x + mm(1.0),
            p.left_inner_side_pad_lower_notch_half_width_y,
            p.left_inner_side_pad_lower_notch_top_z,
        ),
        mode=Mode.SUBTRACT,
    )
    add(make_left_inner_side_pad_slot(p), mode=Mode.SUBTRACT)
    add(
        z_axis_cylinder(
            p.left_inner_side_pad_hole_x,
            p.left_inner_side_pad_hole_y,
            p.left_inner_side_pad_hole_start_z,
            p.left_inner_side_pad_hole_radius,
            p.left_inner_side_pad_hole_end_z - p.left_inner_side_pad_hole_start_z,
        ),
        mode=Mode.SUBTRACT,
    )


def add_left_upper_recess(p: Art3BodyParams = P) -> None:
    """Add the upper left internal flat panel with vertical rounded slots."""
    add(make_left_upper_panel(p), mode=Mode.ADD)
    add(
        z_axis_box(
            p.left_upper_recess_face_x,
            -p.left_upper_recess_half_width_y,
            p.left_upper_recess_bottom_z,
            p.left_upper_cut_inner_x,
            p.left_upper_recess_half_width_y,
            p.left_upper_recess_top_z,
        ),
        mode=Mode.SUBTRACT,
    )

    for y in p.left_upper_slot_centers_y:
        add(
            x_axis_capsule_slot(
                p.left_upper_cut_outer_x,
                p.left_upper_cut_inner_x,
                y,
                p.left_upper_slot_bottom_center_z,
                p.left_upper_slot_top_center_z,
                p.left_upper_slot_radius,
            ),
            mode=Mode.SUBTRACT,
        )

    for y, z in p.left_upper_hole_centers:
        add(
            x_axis_cylinder(
                p.left_upper_cut_outer_x,
                y,
                z,
                p.left_upper_hole_pocket_radius,
                p.left_upper_hole_pocket_inner_x - p.left_upper_cut_outer_x,
            ),
            mode=Mode.SUBTRACT,
        )
        add(
            x_axis_cylinder(
                p.left_upper_cut_outer_x,
                y,
                z,
                p.left_upper_hole_radius,
                p.left_upper_cut_inner_x - p.left_upper_cut_outer_x,
            ),
            mode=Mode.SUBTRACT,
        )

    if p.left_upper_panel_square_cut_enabled:
        half_size = p.left_upper_panel_square_cut_size / 2.0
        center_z = (p.left_upper_recess_bottom_z + p.left_upper_recess_top_z) / 2.0
        add(
            z_axis_box(
                p.left_upper_recess_face_x - mm(1.0),
                -half_size,
                center_z - half_size,
                p.left_upper_recess_face_x + p.left_upper_panel_square_cut_depth,
                half_size,
                center_z + half_size,
            ),
            mode=Mode.SUBTRACT,
        )


def add_right_profile(p: Art3BodyParams = P) -> None:
    """Add the opposite curved-wall profile with side chamfers and lower holes."""
    add(make_right_profile_material(p), mode=Mode.ADD)
    add(make_right_profile_clearance(p), mode=Mode.SUBTRACT)

    hole_depth = p.right_profile_outer_x - p.right_profile_face_x + mm(2.0)
    counterbore_depth = p.right_profile_outer_x - p.right_profile_counterbore_start_x
    for y in p.right_profile_hole_centers_y:
        add(
            x_axis_cylinder(
                p.right_profile_face_x - mm(1.0),
                y,
                p.right_profile_hole_z,
                p.right_profile_hole_radius,
                hole_depth,
            ),
            mode=Mode.SUBTRACT,
        )
        add(
            x_axis_cylinder(
                p.right_profile_counterbore_start_x,
                y,
                p.right_profile_hole_z,
                p.right_profile_counterbore_radius,
                counterbore_depth,
            ),
            mode=Mode.SUBTRACT,
        )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


with BuildPart() as model:
    Cylinder(
        radius=P.base_radius,
        height=P.base_height,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    if P.include_base_recess:
        Cylinder(
            radius=P.base_recess_radius,
            height=P.base_recess_depth,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT,
        )

    if P.bottom_profile_cut_enabled:
        add_bottom_profile_cut(P)

    if P.base_stepped_holes_enabled:
        add_base_stepped_holes(P)

    add(build_main_body_and_dome(P), mode=Mode.ADD)

    if P.shell_enabled:
        add(build_inner_void(P), mode=Mode.SUBTRACT)

    if P.back_features_enabled:
        add_back_features(P)

    if P.top_dome_slots_enabled:
        add_top_dome_slots(P)

    if P.front_inner_pads_enabled:
        add_front_inner_pads(P)

    if P.left_inner_side_pad_enabled:
        add_left_inner_side_pad(P)

    if P.left_upper_recess_enabled:
        add_left_upper_recess(P)

    if P.right_profile_enabled:
        add_right_profile(P)

    if P.front_holes_enabled:
        add_front_holes(P)


result = model.part


# ---------------------------------------------------------------------------
# Export and basic checks
# ---------------------------------------------------------------------------


def print_report() -> None:
    bb = result.bounding_box()
    print("Art3Body hollow main body + dome")
    print(f"  scale: {SCALE:g}")
    print(f"  volume: {result.volume:,.2f} cubic mm")
    print(f"  faces: {len(result.faces())}")
    print(
        "  bbox:"
        f" X {bb.min.X:.3f}..{bb.max.X:.3f},"
        f" Y {bb.min.Y:.3f}..{bb.max.Y:.3f},"
        f" Z {bb.min.Z:.3f}..{bb.max.Z:.3f}"
    )
    print("  dome stations:")
    for y in y_stations(P):
        print(
            f"    Y={y:9.3f}"
            f"  Xhalf={capsule_x_half_width(y):9.3f}"
            f"  seamZ={side_seam_z(y):9.3f}"
            f"  crownZ={crown_z_at_y(y):9.3f}"
        )
    if P.shell_enabled:
        print("  inner stations:")
        for y in inner_y_stations(P):
            print(
                f"    Y={y:9.3f}"
                f"  Xhalf={inner_capsule_x_half_width(y):9.3f}"
                f"  seamZ={inner_side_seam_z(y):9.3f}"
                f"  crownZ={inner_crown_z_at_y(y):9.3f}"
            )
    if P.back_features_enabled:
        print("  back feature:")
        print(
            f"    center=(X {P.back_feature_center_x:.3f},"
            f" Y {P.back_face_y:.3f}, Z {P.back_feature_center_z:.3f})"
        )
        print(
            f"    pad radius {P.back_pad_base_radius:.3f}->{P.back_pad_top_radius:.3f},"
            f" counterbore radius {P.back_body_counterbore_radius:.3f},"
            f" bore radius {P.back_bore_radius:.3f}"
        )
    if P.front_holes_enabled:
        print("  front holes:")
        print(
            f"    3x R{P.front_small_hole_radius:.3f}"
            f" at {P.front_small_hole_centers};"
            f" 1x R{P.front_large_hole_radius:.3f}"
            f" at {P.front_large_hole_center}"
        )


def load_validation_mesh(path: Path):
    import trimesh

    mesh = trimesh.load_mesh(path, force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"{path} did not load as a single Trimesh")
    mesh.remove_unreferenced_vertices()
    return mesh


def validation_bbox_text(mesh) -> str:
    mins, maxs = mesh.bounds
    extents = mesh.extents
    return (
        f"min=({mins[0]:.3f}, {mins[1]:.3f}, {mins[2]:.3f}), "
        f"max=({maxs[0]:.3f}, {maxs[1]:.3f}, {maxs[2]:.3f}), "
        f"extents=({extents[0]:.3f}, {extents[1]:.3f}, {extents[2]:.3f})"
    )


def validation_bbox_diagonal(mesh) -> float:
    import numpy as np

    return float(np.linalg.norm(mesh.extents))


def validation_scaled_copy(mesh, scale: float):
    scaled = mesh.copy()
    scaled.apply_scale(scale)
    return scaled


def validation_nearest_vertex_distances(points, target):
    import numpy as np
    from scipy.spatial import cKDTree

    tree = cKDTree(np.asarray(target.vertices))
    distances, _ = tree.query(points, k=1, workers=-1)
    return distances


def validation_surface_distance_stats(source, target, sample_count: int) -> dict[str, object]:
    import numpy as np
    import trimesh

    points, _ = trimesh.sample.sample_surface(source, sample_count)
    method = "nearest surface"
    try:
        _, distances, _ = target.nearest.on_surface(points)
    except ModuleNotFoundError as exc:
        if exc.name != "rtree":
            raise
        method = "nearest vertex fallback"
        distances = validation_nearest_vertex_distances(points, target)
    return {
        "method": method,
        "mean": float(np.mean(distances)),
        "median": float(np.median(distances)),
        "p95": float(np.percentile(distances, 95)),
        "max": float(np.max(distances)),
    }


def print_validation_distance_stats(label: str, stats: dict[str, object]) -> None:
    print(
        f"{label} ({stats['method']}): mean={stats['mean']:.3f} mm, "
        f"median={stats['median']:.3f} mm, "
        f"p95={stats['p95']:.3f} mm, "
        f"max={stats['max']:.3f} mm"
    )


def try_validation_boolean_symmetric_difference(generated, reference) -> None:
    import trimesh

    try:
        generated_minus_reference = trimesh.boolean.difference([generated, reference])
        reference_minus_generated = trimesh.boolean.difference([reference, generated])
    except BaseException as exc:
        print(f"Boolean symmetric difference: unavailable ({exc})")
        return

    parts = []
    for mesh in [generated_minus_reference, reference_minus_generated]:
        if mesh is None:
            continue
        if isinstance(mesh, trimesh.Scene):
            parts.extend(mesh.dump())
        else:
            parts.append(mesh)

    volume = sum(abs(float(mesh.volume)) for mesh in parts if isinstance(mesh, trimesh.Trimesh))
    print(f"Boolean symmetric-difference volume: {volume:,.3f} cubic mm")


def validate_against_reference(generated_stl: Path, reference_stl: Path = REFERENCE_STL) -> None:
    import numpy as np

    print()
    print("Validation against reference STL")
    if not reference_stl.exists():
        print(f"Reference STL missing: {reference_stl}")
        return

    try:
        generated = load_validation_mesh(generated_stl)
        reference = load_validation_mesh(reference_stl)
    except ImportError as exc:
        print(f"Validation skipped: missing dependency ({exc})")
        return

    print(f"Generated: {generated_stl}")
    print(f"Reference: {reference_stl}")
    print(f"Generated watertight: {generated.is_watertight}")
    print(f"Reference watertight:  {reference.is_watertight}")
    print(f"Generated faces: {len(generated.faces):,}")
    print(f"Reference faces:  {len(reference.faces):,}")
    print(f"Generated bbox:  {validation_bbox_text(generated)}")
    print(f"Reference bbox:   {validation_bbox_text(reference)}")

    generated_volume = abs(float(generated.volume))
    reference_volume = abs(float(reference.volume))
    raw_volume_delta = generated_volume - reference_volume
    raw_volume_delta_percent = (
        100.0 * raw_volume_delta / reference_volume if reference_volume else float("nan")
    )
    print(f"Generated volume: {generated_volume:,.3f} cubic mm")
    print(f"Reference volume:  {reference_volume:,.3f} cubic mm")
    print(
        f"Raw volume delta: {raw_volume_delta:,.3f} cubic mm "
        f"({raw_volume_delta_percent:.3f}%)"
    )

    comparison_reference = reference
    scale = validation_bbox_diagonal(generated) / validation_bbox_diagonal(reference)
    if np.isfinite(scale) and not np.isclose(scale, 1.0, rtol=0.05):
        comparison_reference = validation_scaled_copy(reference, scale)
        scaled_reference_volume = reference_volume * scale**3
        scaled_volume_delta = generated_volume - scaled_reference_volume
        scaled_volume_delta_percent = (
            100.0 * scaled_volume_delta / scaled_reference_volume
            if scaled_reference_volume
            else float("nan")
        )
        print(f"Reference auto-scale for comparison: {scale:.6f}x")
        print(f"Scaled reference volume: {scaled_reference_volume:,.3f} cubic mm")
        print(
            f"Scaled volume delta:    {scaled_volume_delta:,.3f} cubic mm "
            f"({scaled_volume_delta_percent:.3f}%)"
        )
        print(f"Scaled reference bbox:   {validation_bbox_text(comparison_reference)}")

    print(
        f"Approximate symmetric surface distance "
        f"({VALIDATION_SAMPLE_COUNT:,} samples each way):"
    )
    print_validation_distance_stats(
        "generated -> reference",
        generated_to_reference := validation_surface_distance_stats(
            generated,
            comparison_reference,
            VALIDATION_SAMPLE_COUNT,
        ),
    )
    print_validation_distance_stats(
        "reference -> generated",
        reference_to_generated := validation_surface_distance_stats(
            comparison_reference,
            generated,
            VALIDATION_SAMPLE_COUNT,
        ),
    )
    symmetric_mean_distance = (
        float(generated_to_reference["mean"]) + float(reference_to_generated["mean"])
    ) / 2.0
    symmetric_p95_distance = max(
        float(generated_to_reference["p95"]),
        float(reference_to_generated["p95"]),
    )
    surface_difference_volume_proxy = (
        float(generated.area) * float(generated_to_reference["mean"])
        + float(comparison_reference.area) * float(reference_to_generated["mean"])
    ) / 2.0
    print(
        f"Symmetric surface-distance mean: {symmetric_mean_distance:.3f} mm "
        f"(p95 envelope {symmetric_p95_distance:.3f} mm)"
    )
    print(
        "Approximate symmetric-difference volume proxy: "
        f"{surface_difference_volume_proxy:,.3f} cubic mm "
        "(surface-area weighted)"
    )
    try_validation_boolean_symmetric_difference(generated, comparison_reference)


def export_model() -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    step_path = OUTPUT_DIR / f"{OUTPUT_BASENAME}.step"
    stl_path = OUTPUT_DIR / f"{OUTPUT_BASENAME}.stl"
    export_step(result, step_path)
    export_stl(result, stl_path, tolerance=0.05 * SCALE if SCALE else 0.05)
    print(f"STEP saved: {step_path}")
    print(f"STL saved:  {stl_path}")
    return step_path, stl_path


if __name__ == "__main__":
    print_report()
    _, exported_stl = export_model()
    validate_against_reference(exported_stl)
