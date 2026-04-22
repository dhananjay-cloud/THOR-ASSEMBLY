"""
Art3Pulley — Parametric build123d Script
=========================================
A large pulley wheel (3-spoke design):
  • Cylindrical rim body  r=370, Z=0..180
  • Hub solid  r=0..82  (Z=0..180)  |  NO central bore (filled solid)
  • Inner ring r=82..170 — SOLID throughout (connects hub to spoke web)
  • 2× spoke web openings (annular sectors r=170..320, full height Z=0..180):
      Opening A: 11.18° → 168.82°  (157.6°, large — top/right)
      Opening B: 251.18° → 288.82° ( 37.6°, small — bottom)
  • Arm/bracket restores solid material in opening A top region (Y=195..295)
  • 8× spoke bore holes r=20 at spoke-wall junctions (r=300 and r=190)
  • 3× counterbored fixing holes at (0,−180), (±160,130)
  • Keyway slot + horizontal bores in arm
  • 2× counterbored shaft holes at (±110, 0)

Dependencies:
    pip install build123d cadquery trimesh manifold3d scipy ocp-vscode
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
#  OUTPUT PATHS
# ══════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR = "/Users/softage/Desktop/New-boston-py-files/Thor-stl/Assem-Art3-build123d"
_base      = os.path.join(OUTPUT_DIR, "Art3Pulley_parametric_pure")
REFERENCE_STEP_PATH = os.path.join(OUTPUT_DIR, "Art3Pulley-faces.step")

# ══════════════════════════════════════════════════════════════════════════════
#  PARAMETERS  (all dimensions in mm)
# ══════════════════════════════════════════════════════════════════════════════

# ── Rim ───────────────────────────────────────────────────────────────────────
rim_radius      = 370.0
total_height    = 180.0
sphere_radius   = 400.281
sphere_z_centre =  15.0
lower_height    =  30.0    # sphere-wall section
bottom_cut_overlap = 0.2   # lets bottom-starting cuts pass cleanly through z=0

# ── Hub ───────────────────────────────────────────────────────────────────────
hub_bore_r      =  50.0    # central bore radius (UNUSED — filled solid)
hub_step_z      =  90.0
bottom_center_pocket_r     =  82.0
bottom_center_pocket_depth =  90.0

# ── Top-face spoke window profile ────────────────────────────────────────────
# The r=20 features are rounded window ends, not standalone through holes.
spoke_r_inner   = 170.0
spoke_r_outer   = 320.0

# Segment definitions are source-derived dimensions baked into the model so
# the script is parametric and does not read profile files at runtime.
top_profile_mirror_y = True
top_web_segments = [
    ("arc",  294.309455, -58.154444,  20.000015, 257.841972, 345.980938),
    ("line", 290.094294, -77.717786, 181.566352, -48.638214),
    ("arc",  187.682685, -29.583906,  19.999994, 173.838862, 252.202532),
    ("arc",   -0.033724,  -0.019472, 170.037161,  -9.278308,  69.278310),
    ("arc",   68.220941, 177.329935,  20.000007, 167.797484, 246.161111),
    ("line",  48.661245, 181.560187,  77.741575, 290.087922),
    ("arc",   96.791486, 283.956710,  19.999991,  74.019003, 162.158071),
    ("arc",    0.025465,   0.014705, 319.972077, -11.358513,  71.358512),
    ("arc",    0.033724,  -0.019472, 170.037161, 110.721690, 189.278308),
    ("arc", -187.682685, -29.583906,  19.999994, -72.202532,   6.161138),
    ("line",-181.566352, -48.638214,-290.094294, -77.717786),
    ("arc", -294.309455, -58.154444,  20.000015, 194.019062, 282.158028),
    ("arc",   -0.025465,   0.014705, 319.972077, 108.641488, 191.358512),
    ("arc",  -96.791486, 283.956710,  19.999991,  17.841929, 105.980997),
    ("line", -77.741575, 290.087922, -48.661245, 181.560187),
    ("arc",  -68.220941, 177.329935,  20.000007, -66.161111,  12.202516),
]

# ── Spoke bore holes ×8 (r=20, full height) ──────────────────────────────────
spoke_bore_r    =  20.0
spoke_bore_positions = [
    (-294.309,   58.154),   # outer group  r≈300
    ( -96.791, -283.957),
    (  96.791, -283.957),
    ( 294.309,   58.154),
    (-187.683,   29.584),   # inner group  r≈190
    ( -68.221, -177.330),
    (  68.221, -177.330),
    ( 187.683,   29.584),
]

# ── Fixing holes ×3 ──────────────────────────────────────────────────────────
fix_hole_positions = [(0, -180), (-160, 130), (160, 130)]
fix_cbore_r     =  29.5
fix_bore_r      =  17.0
fix_cbore_depth =  30.0

# ── Arm / bracket ─────────────────────────────────────────────────────────────
arm_x_half      = 115.0
arm_y_start     = 195.0
arm_y_end       = 230.0
arm_height      = 130.0

# ── Gussets ───────────────────────────────────────────────────────────────────
gusset_x_inner  =  50.0
gusset_x_outer  = 115.0
gusset_y_start  = 230.0
gusset_y_end    = 295.0

# ── Keyway slot ───────────────────────────────────────────────────────────────
kw_x_half       =  29.012
kw_y_inner      = 243.5
kw_y_outer      = 273.5
kw_rect_top_z   =  81.75
kw_slope_top_z  =  98.5
kw_bore_r       =  17.0
kw_bore_z       =  65.0

# ── STEP-derived rectangular notches at the central r=50 bore ────────────────
central_notch_x_outer =  80.9881496429443
central_notch_y_half  =  16.749999434163
central_notch_z1      =  70.0
central_notch_z2      =  90.0

# ── Side counterbored holes ×2 at (±110, 0) ──────────────────────────────────
side_hole_x     = 110.0
side_bore_r     =  17.0
side_bore_z1    =  40.0
side_bore_z2    =  70.0
side_cbore_r    =  33.5

# ── Bottom-face cut profiles ─────────────────────────────────────────────────
bottom_middle_cut_depth = 40.0
bottom_remaining_cut_depth = 130.0
bottom_middle_profile = [
    ( 153.000002, -35.0, 0.0),
    ( 153.000002,  35.0, 0.0),
    (  74.155243,  35.0, 0.290212),
    (   0.000000,  82.0, 0.290212),
    ( -74.155243,  35.0, 0.0),
    (-153.000002,  35.0, 0.0),
    (-153.000002, -35.0, 0.0),
    ( -74.155243, -35.0, 0.290212),
    (   0.000000, -82.0, 0.290212),
    (  74.155243, -35.0, 0.0),
]
bottom_remaining_segments = [
    ("line", -50.0, 295.0, -50.0, 396.863074),
    ("line",  50.0, 396.863074, 50.0, 295.0),
    ("line",-115.0, 195.0,-115.0, 230.0),
    ("line", 115.0, 195.0,-115.0, 195.0),
    ("line",-115.0, 230.0, -50.0, 295.0),
    ("line",  50.0, 295.0, 115.0, 230.0),
    ("line", 115.0, 230.0, 115.0, 195.0),
    ("line", -25.0, 295.0, -90.0, 230.0),
    ("line",  25.0, 295.0,  25.0, 399.217987),
    ("line", -90.0, 230.0,  90.0, 230.0),
    ("line", -25.0, 399.217987, -25.0, 295.0),
    ("line",  90.0, 230.0,  25.0, 295.0),
    ("arc",    0.0,   0.0, 400.000002, 93.583322, 97.180756),
    ("arc",    0.0,   0.0, 400.000002, 82.819244, 86.416678),
]

# ══════════════════════════════════════════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════════════════════════════════════════

_BIG = rim_radius * 3


def _arc_points(center, radius, start_deg, end_deg, ccw=True, segments=24):
    """Sample arc points. Angles are in degrees in the XY plane."""
    if ccw:
        if end_deg < start_deg:
            end_deg += 360.0
        angles = [start_deg + (end_deg - start_deg) * i / segments
                  for i in range(segments + 1)]
    else:
        if start_deg < end_deg:
            start_deg += 360.0
        angles = [start_deg + (end_deg - start_deg) * i / segments
                  for i in range(segments + 1)]

    cx, cy = center
    return [
        (
            cx + radius * math.cos(math.radians(a)),
            cy + radius * math.sin(math.radians(a)),
        )
        for a in angles
    ]


def _append_segment(points, segment):
    if points and segment:
        segment = segment[1:]
    points.extend(segment)


def _top_profile_xy(x, y):
    return (x, -y if top_profile_mirror_y else y)


def _segments_to_pieces(segments_data, transform=lambda x, y: (x, y),
                        arc_segments=16):
    pieces = []
    for segment in segments_data:
        kind = segment[0]
        if kind == "line":
            _, x1, y1, x2, y2 = segment
            pieces.append([transform(x1, y1), transform(x2, y2)])
        elif kind == "arc":
            _, cx, cy, radius, start, end = segment
            if end < start:
                end += 360.0
            pts = []
            for i in range(arc_segments + 1):
                angle = start + (end - start) * i / arc_segments
                pts.append(transform(
                    cx + radius * math.cos(math.radians(angle)),
                    cy + radius * math.sin(math.radians(angle)),
                ))
            pieces.append(pts)
        else:
            raise ValueError(f"Unsupported segment type: {kind}")
    return pieces


def _assemble_loops(pieces, tol=0.05):
    def dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    unused = list(range(len(pieces)))
    loops = []
    while unused:
        idx = unused.pop(0)
        loop = pieces[idx][:]
        changed = True
        while changed:
            changed = False
            for j in unused[:]:
                piece = pieces[j]
                if dist(loop[-1], piece[0]) < tol:
                    loop.extend(piece[1:])
                elif dist(loop[-1], piece[-1]) < tol:
                    loop.extend(reversed(piece[:-1]))
                elif dist(loop[0], piece[-1]) < tol:
                    loop = piece[:-1] + loop
                elif dist(loop[0], piece[0]) < tol:
                    loop = list(reversed(piece[1:])) + loop
                else:
                    continue
                unused.remove(j)
                changed = True
                break
        loops.append(loop)
    return loops


def _top_web_window_loops():
    """Top web-window loops from parametric segment definitions."""
    pieces = _segments_to_pieces(top_web_segments, _top_profile_xy,
                                 arc_segments=16)
    return [loop for loop in _assemble_loops(pieces, tol=0.05)
            if len(loop) > 20]


def _side_cbore_restore_cap_points(sx):
    """Small circular cap restored after cutting the side counterbore.

    The source profile has a D-shaped opening: a full r=33.5 counterbore clipped
    by a vertical chord at x=±80.988. Robustly model it by subtracting the full
    cylinder and adding this small cap back.
    """
    if sx < 0:
        return [(-x, y) for x, y in reversed(_side_cbore_restore_cap_points(1))]

    # Local coordinates: this tool is added inside Locations((±110, 0, z)).
    chord_x = -(side_hole_x - 80.98814964325852)
    cx = 0.0
    r = side_cbore_r
    y = 16.74999943416299

    pts = [(chord_x, -y), (chord_x, y)]
    _append_segment(pts, _arc_points((cx, 0), r, 150.0, -150.0,
                                     ccw=True, segments=16))
    return pts


def _side_cbore_d_tool(sx, height):
    """D-shaped side counterbore subtract tool, clipped to the source chord."""
    chord = -sx * (side_hole_x - 80.98814964325852)
    with BuildPart() as tool:
        Cylinder(radius=side_cbore_r, height=height,
                 align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((chord - sx * _BIG / 2, 0, height / 2)):
            Box(_BIG, _BIG, height + 2,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
    return tool.part


def _profile_cut_tool(points, height, z_start=0.0):
    with BuildSketch(Plane.XY.offset(z_start)) as _sk:
        with BuildLine():
            Polyline(points, close=True)
        make_face()
    return extrude(_sk.sketch, amount=height)


def _bulge_segment_points(start, end, bulge, segments=16):
    """Sample a polyline bulge arc without external profile libraries."""
    if abs(bulge) < 1e-9:
        return [end]

    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    chord = math.hypot(dx, dy)
    theta = 4.0 * math.atan(bulge)
    radius = abs(chord / (2.0 * math.sin(theta / 2.0)))
    offset = chord / (2.0 * math.tan(theta / 2.0))
    mx = (x1 + x2) / 2.0
    my = (y1 + y2) / 2.0
    cx = mx - dy / chord * offset
    cy = my + dx / chord * offset

    a1 = math.atan2(y1 - cy, x1 - cx)
    a2 = math.atan2(y2 - cy, x2 - cx)
    if bulge > 0:
        if a2 < a1:
            a2 += 2.0 * math.pi
    else:
        if a1 < a2:
            a1 += 2.0 * math.pi

    pts = []
    for i in range(1, segments + 1):
        angle = a1 + (a2 - a1) * i / segments
        pts.append((cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle)))
    return pts


def _bottom_middle_cut_loop():
    """Closed central bottom profile from parametric bulge data."""
    points = [(bottom_middle_profile[0][0], bottom_middle_profile[0][1])]
    count = len(bottom_middle_profile)
    for i, item in enumerate(bottom_middle_profile):
        x1, y1, bulge = item
        x2, y2, _ = bottom_middle_profile[(i + 1) % count]
        points.extend(_bulge_segment_points((x1, y1), (x2, y2), bulge))
    return points


def _bottom_remaining_cut_loop():
    """Outer/top portion of the keyway-side bottom profile."""
    pts = [
        (50.0000017637425, 396.86269845328843),
        (50.0, 295.0),
        (115.0, 230.0),
        (115.0, 195.0),
        (-115.0, 195.0),
        (-115.0, 230.0),
        (-50.0, 295.0),
        (-50.00000176374246, 396.8626984532885),
    ]
    _append_segment(pts, _arc_points((0.0, -0.000000760766), 400.000002,
                                     97.180756, 93.583322,
                                     ccw=False, segments=16))
    pts.extend([
        (-25.0, 295.0),
        (-90.0, 230.0),
        (90.0, 230.0),
        (25.0, 295.0),
        (25.0000022259473, 399.2179874313063),
    ])
    _append_segment(pts, _arc_points((0.0, -0.000000760766), 400.000002,
                                     86.416678, 82.819244,
                                     ccw=False, segments=16))
    return pts


def _bottom_remaining_side_loops():
    """Simple sub-profiles for the lower/side bands of the 130 mm bottom cut."""
    return [
        [(-115.0, 195.0), (115.0, 195.0),
         (115.0, 230.0), (-115.0, 230.0)],
        [(-115.0, 230.0), (-50.0, 295.0),
         (-25.0, 295.0), (-90.0, 230.0)],
        [(90.0, 230.0), (25.0, 295.0),
         (50.0, 295.0), (115.0, 230.0)],
    ]


def _bottom_remaining_clean_loops():
    """Non-overlapping 130 mm bottom cut profiles from botton_cut_profile.dxf.

    The DXF describes this region as line and arc segments surrounding the
    small keyway rectangle. Building one long profile creates a self-crossing
    sketch in the notch area, so keep the five source regions separate.
    """
    center = (0.0, -0.000000760766)
    radius = 400.000002

    left_outer_strip = [
        (-50.0, 295.0),
        (-50.00000176374246, 396.8626984532885),
    ]
    _append_segment(
        left_outer_strip,
        _arc_points(center, radius, 97.180756, 93.583322,
                    ccw=False, segments=20),
    )
    left_outer_strip.append((-25.0, 295.0))

    right_outer_strip = [
        (25.0, 295.0),
        (25.0000022259473, 399.2179874313063),
    ]
    _append_segment(
        right_outer_strip,
        _arc_points(center, radius, 86.416678, 82.819244,
                    ccw=False, segments=20),
    )
    right_outer_strip.append((50.0, 295.0))

    return [
        [(-115.0, 195.0), (115.0, 195.0),
         (115.0, 230.0), (-115.0, 230.0)],
        [(-115.0, 230.0), (-50.0, 295.0),
         (-25.0, 295.0), (-90.0, 230.0)],
        [(90.0, 230.0), (25.0, 295.0),
         (50.0, 295.0), (115.0, 230.0)],
        left_outer_strip,
        right_outer_strip,
    ]


def _annular_sector_tool(r_inner, r_outer, height, start_deg, end_deg,
                         z_start=0.0):
    sweep = end_deg - start_deg
    if sweep <= 0:
        sweep += 360.0

    outer_start = (
        r_outer * math.cos(math.radians(start_deg)),
        r_outer * math.sin(math.radians(start_deg)),
    )
    outer_end = (
        r_outer * math.cos(math.radians(end_deg)),
        r_outer * math.sin(math.radians(end_deg)),
    )
    inner_start = (
        r_inner * math.cos(math.radians(start_deg)),
        r_inner * math.sin(math.radians(start_deg)),
    )
    inner_end = (
        r_inner * math.cos(math.radians(end_deg)),
        r_inner * math.sin(math.radians(end_deg)),
    )

    with BuildSketch(Plane.XY.offset(z_start)) as _sk:
        with BuildLine():
            CenterArc((0, 0), r_outer, start_deg, sweep)
            Line(outer_end, inner_end)
            CenterArc((0, 0), r_inner, end_deg, -sweep)
            Line(inner_start, outer_start)
        make_face()
    return extrude(_sk.sketch, amount=height)


def _bottom_remaining_cut_tool(height):
    """Rim-only cleanup trims for the keyway-side bottom cut."""
    with BuildPart() as tool:
        # The outer arcs sit on the same r=400 bottom circumference as the base.
        # Trim a 1.5 mm annular strip over those two arc spans only; this clears
        # the skin at the outer rim without adding rectangular bites to the
        # straight profile edges.
        add(_annular_sector_tool(398.5, 405.0, height, 82.81924431673289,
                                 86.4166783782907,
                                 z_start=-bottom_cut_overlap))
        add(_annular_sector_tool(398.5, 405.0, height, 93.58332173486744,
                                 97.18075579754321,
                                 z_start=-bottom_cut_overlap))
    return tool.part


def _central_bore_notch_tool(sx):
    """Small rectangular notch from STEP at the central r=50 bore."""
    # Extend the cutter through the already-empty central bore. Starting the
    # box almost tangent to r=50 leaves a tiny trimmed sliver that STL meshing
    # can export as open edges.
    x0 = 0.0
    x1 = sx * central_notch_x_outer
    xmin, xmax = sorted((x0, x1))
    width = xmax - xmin
    height = central_notch_z2 - central_notch_z1
    with BuildPart() as tool:
        with Locations(((xmin + xmax) / 2, 0,
                        central_notch_z1 + height / 2)):
            Box(width, central_notch_y_half * 2, height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER))
    return tool.part


def _repair_stl_watertight_generic_capper_disabled(stl_path, digits=5):
    """Close STL meshing cracks without changing the CAD model.

    OCC exports this part as a valid-looking triangle mesh, but the bottom
    coplanar trimmed faces and two notch seams can contain open mesh edges.
    This repair merges micron-level duplicate vertices and caps only planar
    boundary cycles, then writes the watertight mesh back to the STL path.
    """
    try:
        import numpy as np
        import trimesh
        from collections import defaultdict
        from scipy.spatial import Delaunay
    except Exception as exc:
        print(f"STL repair skipped : {exc}")
        return False

    def _edge_info(mesh):
        counts = np.bincount(mesh.edges_unique_inverse)
        return mesh.edges_unique[counts == 1], mesh.edges_unique[counts > 2]

    def _boundary_walks(edges):
        adj = defaultdict(list)
        for a, b in edges:
            adj[int(a)].append(int(b))
            adj[int(b)].append(int(a))

        used = set()
        loops = []
        for a, b in edges.tolist():
            edge = tuple(sorted((int(a), int(b))))
            if edge in used:
                continue

            start, current = edge
            previous = start
            loop = [start, current]
            used.add(edge)

            for _ in range(len(edges) + 20):
                candidates = [
                    n for n in adj[current]
                    if tuple(sorted((current, n))) not in used
                ]
                if not candidates:
                    break

                next_vertex = None
                for n in candidates:
                    if n == start and len(loop) >= 3:
                        next_vertex = n
                        break
                if next_vertex is None:
                    for n in candidates:
                        if n != previous:
                            next_vertex = n
                            break
                if next_vertex is None:
                    next_vertex = candidates[0]

                used.add(tuple(sorted((current, next_vertex))))
                previous, current = current, next_vertex
                if current == start:
                    break
                loop.append(current)

            loops.append(loop)
        return loops

    def _point_in_polygon(point, polygon):
        x, y = point
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if (yi > y) != (yj > y):
                x_intersect = (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi
                if x < x_intersect:
                    inside = not inside
            j = i
        return inside

    def _orient_planar_face(face, vertices, dropped_axis):
        p0, p1, p2 = vertices[face]
        normal = np.cross(p1 - p0, p2 - p0)
        if dropped_axis == 2 and normal[2] > 0:
            return [face[0], face[2], face[1]]
        return face

    def _unique_projected_loop(loop, vertices, keep_axes):
        unique = []
        seen = set()
        for idx in loop:
            key = tuple(np.round(vertices[idx][keep_axes], digits))
            if key not in seen:
                seen.add(key)
                unique.append(idx)
        return unique

    def _triangulate_loop(loop, vertices, use_delaunay=True):
        pts3 = vertices[loop]
        ranges = np.ptp(pts3, axis=0)
        if np.min(ranges) > 1e-5:
            return []

        dropped_axis = int(np.argmin(ranges))
        keep_axes = [i for i in range(3) if i != dropped_axis]
        unique = _unique_projected_loop(loop, vertices, keep_axes)
        if len(unique) < 3:
            return []

        if not use_delaunay:
            return [
                _orient_planar_face(
                    [unique[0], unique[i], unique[i + 1]],
                    vertices,
                    dropped_axis,
                )
                for i in range(1, len(unique) - 1)
            ]

        pts2 = vertices[unique][:, keep_axes]
        triangles = (
            np.array([[0, 1, 2]])
            if len(unique) == 3
            else Delaunay(pts2).simplices
        )

        faces = []
        for triangle in triangles:
            centroid = pts2[triangle].mean(axis=0)
            if len(unique) == 3 or _point_in_polygon(centroid, pts2):
                face = [unique[int(i)] for i in triangle]
                faces.append(_orient_planar_face(face, vertices, dropped_axis))
        return faces

    def _add_faces(mesh, faces):
        if not faces:
            return mesh
        patched = trimesh.util.concatenate([
            mesh,
            trimesh.Trimesh(
                vertices=mesh.vertices.copy(),
                faces=np.array(faces),
                process=False,
            ),
        ])
        patched.merge_vertices(digits_vertex=digits)
        patched.remove_unreferenced_vertices()
        return patched

    def _boundary_components(edges):
        adj = defaultdict(set)
        for a, b in edges:
            adj[int(a)].add(int(b))
            adj[int(b)].add(int(a))

        seen = set()
        components = []
        for vertex in list(adj):
            if vertex in seen:
                continue
            stack = [vertex]
            seen.add(vertex)
            component = []
            while stack:
                current = stack.pop()
                component.append(current)
                for neighbor in adj[current]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            component_set = set(component)
            components.append({
                item: adj[item] & component_set
                for item in component
            })
        return components

    def _cycle_basis(adj):
        remaining = set(adj)
        cycles = []
        while remaining:
            root = remaining.pop()
            stack = [root]
            predecessor = {root: root}
            used = {root: set()}
            while stack:
                current = stack.pop()
                current_used = used[current]
                for neighbor in adj[current]:
                    if neighbor not in used:
                        predecessor[neighbor] = current
                        stack.append(neighbor)
                        used[neighbor] = {current}
                    elif neighbor not in current_used and neighbor != current:
                        previous_used = used[neighbor]
                        cycle = [neighbor, current]
                        parent = predecessor[current]
                        while parent not in previous_used:
                            cycle.append(parent)
                            parent = predecessor[parent]
                        cycle.append(parent)
                        cycles.append(cycle)
                        used[neighbor].add(current)
                remaining.discard(current)
        return cycles

    mesh = trimesh.load(stl_path, force="mesh", process=True)
    before_volume = mesh.volume
    mesh.merge_vertices(digits_vertex=digits)
    mesh.remove_unreferenced_vertices()

    boundary, nonmanifold = _edge_info(mesh)
    if mesh.is_watertight and mesh.is_volume and len(nonmanifold) == 0:
        print("STL repair : already watertight")
        return True

    faces = []
    for loop in _boundary_walks(boundary):
        faces.extend(_triangulate_loop(loop, mesh.vertices, use_delaunay=True))
    mesh = _add_faces(mesh, faces)
    first_pass_faces = len(faces)

    faces = []
    boundary, _ = _edge_info(mesh)
    for component in _boundary_components(boundary):
        for cycle in _cycle_basis(component):
            faces.extend(_triangulate_loop(cycle, mesh.vertices,
                                           use_delaunay=False))
    mesh = _add_faces(mesh, faces)
    second_pass_faces = len(faces)

    try:
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fix_inversion(mesh)
    except Exception:
        pass
    mesh.process(validate=True)
    mesh.merge_vertices(digits_vertex=digits)
    mesh.remove_unreferenced_vertices()

    boundary, nonmanifold = _edge_info(mesh)
    mesh.export(stl_path)
    print(
        "STL repair : "
        f"watertight={mesh.is_watertight}, is_volume={mesh.is_volume}, "
        f"open_edges={len(boundary)}, nonmanifold_edges={len(nonmanifold)}, "
        f"cap_faces={first_pass_faces + second_pass_faces}, "
        f"volume_delta={mesh.volume - before_volume:+.4f} mm³"
    )
    return mesh.is_watertight and mesh.is_volume and len(boundary) == 0


def _repair_stl_watertight_bottom_rebuild_disabled(stl_path, digits=5):
    """Rebuild the bottom STL skin while preserving all real openings.

    The CAD model is fine, but the STL export can leave open edges where many
    bottom cuts meet the planar z=0 face. A generic hole-fill closes those
    openings visually, so this version replaces only the bottom material face:
    outer disk minus the actual cutout profiles.
    """
    try:
        import numpy as np
        import trimesh
        from collections import defaultdict
        from scipy.spatial import Delaunay
    except Exception as exc:
        print(f"STL repair skipped : {exc}")
        return False

    def _edge_info(mesh):
        counts = np.bincount(mesh.edges_unique_inverse)
        return mesh.edges_unique[counts == 1], mesh.edges_unique[counts > 2]

    def _point_in_polygon(point, polygon):
        x, y = point
        inside = False
        j = len(polygon) - 1
        for i in range(len(polygon)):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if (yi > y) != (yj > y):
                x_intersect = (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi
                if x < x_intersect:
                    inside = not inside
            j = i
        return inside

    def _orient_bottom(face, vertices):
        p0, p1, p2 = vertices[face]
        normal = np.cross(p1 - p0, p2 - p0)
        if normal[2] > 0:
            return [face[0], face[2], face[1]]
        return face

    void_polys = []
    void_polys.extend(_top_web_window_loops())
    void_polys.append(_bottom_middle_cut_loop())
    void_polys.append(_bottom_remaining_cut_loop())
    void_polys.extend(_bottom_remaining_side_loops())
    void_polys.append([
        (-kw_x_half, kw_y_inner),
        ( kw_x_half, kw_y_inner),
        ( kw_x_half, kw_y_outer),
        (-kw_x_half, kw_y_outer),
    ])

    bottom_holes = [(0.0, 0.0, bottom_center_pocket_r)]
    bottom_holes.extend((x, y, fix_cbore_r) for x, y in fix_hole_positions)

    # z=0 is the planar cut face of the lower spherical lip; its radius is 400.
    outer_bottom_r = math.sqrt(
        max(sphere_radius ** 2 - sphere_z_centre ** 2, 0.0)
    ) + 0.02

    def _is_bottom_material(point):
        x, y = point
        if x * x + y * y > outer_bottom_r * outer_bottom_r:
            return False
        for cx, cy, radius in bottom_holes:
            if (x - cx) ** 2 + (y - cy) ** 2 < (radius - 0.01) ** 2:
                return False
        return not any(_point_in_polygon(point, poly) for poly in void_polys)

    def _boundary_components(edges):
        adj = defaultdict(set)
        for a, b in edges:
            adj[int(a)].add(int(b))
            adj[int(b)].add(int(a))

        seen = set()
        components = []
        for vertex in list(adj):
            if vertex in seen:
                continue
            stack = [vertex]
            seen.add(vertex)
            component = []
            while stack:
                current = stack.pop()
                component.append(current)
                for neighbor in adj[current]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            component_set = set(component)
            components.append({
                item: adj[item] & component_set
                for item in component
            })
        return components

    def _cycle_basis(adj):
        remaining = set(adj)
        cycles = []
        while remaining:
            root = remaining.pop()
            stack = [root]
            predecessor = {root: root}
            used = {root: set()}
            while stack:
                current = stack.pop()
                current_used = used[current]
                for neighbor in adj[current]:
                    if neighbor not in used:
                        predecessor[neighbor] = current
                        stack.append(neighbor)
                        used[neighbor] = {current}
                    elif neighbor not in current_used and neighbor != current:
                        previous_used = used[neighbor]
                        cycle = [neighbor, current]
                        parent = predecessor[current]
                        while parent not in previous_used:
                            cycle.append(parent)
                            parent = predecessor[parent]
                        cycle.append(parent)
                        cycles.append(cycle)
                        used[neighbor].add(current)
                remaining.discard(current)
        return cycles

    def _find_vertex(mesh, xy):
        deltas = np.linalg.norm(mesh.vertices[:, :2] - np.array(xy), axis=1)
        deltas += np.abs(mesh.vertices[:, 2]) * 1000.0
        return int(np.argmin(deltas))

    def _add_faces(mesh, faces):
        if not faces:
            return mesh
        patched = trimesh.util.concatenate([
            mesh,
            trimesh.Trimesh(
                vertices=mesh.vertices.copy(),
                faces=np.array(faces),
                process=False,
            ),
        ])
        patched.merge_vertices(digits_vertex=digits)
        patched.remove_unreferenced_vertices()
        return patched

    mesh = trimesh.load(stl_path, force="mesh", process=True)
    before_volume = mesh.volume
    mesh.merge_vertices(digits_vertex=digits)
    mesh.remove_unreferenced_vertices()

    bottom_faces = np.all(np.abs(mesh.vertices[mesh.faces][:, :, 2]) < 1e-5,
                          axis=1)
    mesh = trimesh.Trimesh(
        vertices=mesh.vertices.copy(),
        faces=mesh.faces[~bottom_faces].copy(),
        process=False,
    )
    mesh.merge_vertices(digits_vertex=digits)
    mesh.remove_unreferenced_vertices()

    bottom_indices = np.where(np.abs(mesh.vertices[:, 2]) < 1e-5)[0]
    unique = []
    seen = set()
    for idx in bottom_indices:
        key = tuple(np.round(mesh.vertices[idx, :2], digits))
        if key not in seen:
            seen.add(key)
            unique.append(idx)

    pts2 = mesh.vertices[unique, :2]
    bottom_faces_new = []
    if len(unique) >= 3:
        for triangle in Delaunay(pts2).simplices:
            centroid = pts2[triangle].mean(axis=0)
            if _is_bottom_material(centroid):
                face = [unique[int(i)] for i in triangle]
                bottom_faces_new.append(_orient_bottom(face, mesh.vertices))
    mesh = _add_faces(mesh, bottom_faces_new)

    residual_faces = []
    boundary, _ = _edge_info(mesh)
    for component in _boundary_components(boundary):
        for cycle in _cycle_basis(component):
            unique_cycle = []
            seen_cycle = set()
            for idx in cycle:
                key = tuple(np.round(mesh.vertices[idx, :2], digits))
                if key not in seen_cycle:
                    seen_cycle.add(key)
                    unique_cycle.append(idx)
            if len(unique_cycle) < 3:
                continue
            for i in range(1, len(unique_cycle) - 1):
                residual_faces.append(_orient_bottom(
                    [unique_cycle[0], unique_cycle[i], unique_cycle[i + 1]],
                    mesh.vertices,
                ))
    mesh = _add_faces(mesh, residual_faces)

    # The residual graph around the keyway lower edge is a bow-tie. Remove
    # overlapping residual triangles on that edge, then add the two material
    # triangles that preserve the rectangular keyway opening.
    key_left = np.array([-kw_x_half, kw_y_inner])
    key_right = np.array([kw_x_half, kw_y_inner])
    remove_faces = []
    for i, face in enumerate(mesh.faces):
        pts = mesh.vertices[face]
        if not np.all(np.abs(pts[:, 2]) < 1e-5):
            continue
        has_left = np.any(np.linalg.norm(pts[:, :2] - key_left, axis=1) < 1e-4)
        has_right = np.any(np.linalg.norm(pts[:, :2] - key_right, axis=1) < 1e-4)
        if not (has_left and has_right):
            continue
        third = [
            p for p in pts[:, :2]
            if np.linalg.norm(p - key_left) > 1e-4
            and np.linalg.norm(p - key_right) > 1e-4
        ]
        if third and np.linalg.norm(third[0]) > 100.0:
            remove_faces.append(i)

    if remove_faces:
        mesh = trimesh.Trimesh(
            vertices=mesh.vertices.copy(),
            faces=np.delete(mesh.faces, remove_faces, axis=0),
            process=False,
        )
        mesh.merge_vertices(digits_vertex=digits)
        mesh.remove_unreferenced_vertices()

    bridge_faces = []

    try:
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fix_inversion(mesh)
    except Exception:
        pass
    mesh.process(validate=True)
    mesh.merge_vertices(digits_vertex=digits)
    mesh.remove_unreferenced_vertices()

    boundary, nonmanifold = _edge_info(mesh)
    mesh.export(stl_path)
    print(
        "STL repair : "
        f"watertight={mesh.is_watertight}, is_volume={mesh.is_volume}, "
        f"open_edges={len(boundary)}, nonmanifold_edges={len(nonmanifold)}, "
        f"bottom_faces={len(bottom_faces_new)}, "
        f"residual_faces={len(residual_faces) + len(bridge_faces)}, "
        f"volume_delta={mesh.volume - before_volume:+.4f} mm³"
    )
    return mesh.is_watertight and mesh.is_volume and len(boundary) == 0


def _repair_stl_watertight(stl_path, digits=4):
    """Make the STL watertight without altering visible feature faces.

    The CAD-overlapped cuts export with the correct features. The remaining STL
    issue is only tiny duplicate/degenerate seams on the shallow bottom middle
    profile, so a conservative mesh cleanup is enough.
    """
    try:
        import numpy as np
        import trimesh
    except Exception as exc:
        print(f"STL repair skipped : {exc}")
        return False

    mesh = trimesh.load(stl_path, force="mesh", process=True)
    before_volume = mesh.volume

    for _ in range(3):
        try:
            mesh.remove_degenerate_faces()
        except Exception:
            pass
        try:
            mesh.remove_duplicate_faces()
        except Exception:
            pass
        mesh.merge_vertices(digits_vertex=digits)
        mesh.remove_unreferenced_vertices()
        try:
            trimesh.repair.fix_normals(mesh)
            trimesh.repair.fix_inversion(mesh)
        except Exception:
            pass
        mesh.process(validate=True)

    counts = np.bincount(mesh.edges_unique_inverse)
    open_edges = int((counts == 1).sum())
    nonmanifold_edges = int((counts > 2).sum())
    mesh.export(stl_path)
    print(
        "STL repair : "
        f"watertight={mesh.is_watertight}, is_volume={mesh.is_volume}, "
        f"open_edges={open_edges}, nonmanifold_edges={nonmanifold_edges}, "
        f"merge_digits={digits}, "
        f"volume_delta={mesh.volume - before_volume:+.4f} mm³"
    )
    return mesh.is_watertight and mesh.is_volume and open_edges == 0


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD
# ══════════════════════════════════════════════════════════════════════════════

with BuildPart() as part:

    # 1. STEP-derived body stack:
    #    lower spherical lip z=0..30, then straight top rim r=370 z=30..180.
    with BuildPart() as _lower_lip:
        with Locations((0, 0, sphere_z_centre)):
            Sphere(radius=sphere_radius)
        with Locations((0, 0, -_BIG / 2)):
            Box(_BIG, _BIG, _BIG,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
        with Locations((0, 0, lower_height + _BIG / 2)):
            Box(_BIG, _BIG, _BIG,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT)
    add(_lower_lip.part)

    with Locations((0, 0, lower_height)):
        Cylinder(radius=rim_radius, height=total_height - lower_height,
                 align=(Align.CENTER, Align.CENTER, Align.MIN),
                 mode=Mode.ADD)

    # 2. Spoke web openings — parametric top-face loops
    for _window in _top_web_window_loops():
        add(_profile_cut_tool(
            _window,
            total_height + 2 * bottom_cut_overlap,
            z_start=-bottom_cut_overlap,
        ), mode=Mode.SUBTRACT)

    # 3. Central bore — through hole across full body
    with Locations((0, 0, -bottom_cut_overlap)):
        Cylinder(radius=hub_bore_r,
                 height=total_height + 2 * bottom_cut_overlap,
                 align=(Align.CENTER, Align.CENTER, Align.MIN),
                 mode=Mode.SUBTRACT)
    with Locations((0, 0, -bottom_cut_overlap)):
        Cylinder(radius=bottom_center_pocket_r,
                 height=bottom_center_pocket_depth + bottom_cut_overlap,
                 align=(Align.CENTER, Align.CENTER, Align.MIN),
                 mode=Mode.SUBTRACT)
    for sx in [-1, +1]:
        add(_central_bore_notch_tool(sx), mode=Mode.SUBTRACT)

    # 4. Fixing holes ×3
    for hx, hy in fix_hole_positions:
        with Locations((hx, hy, -bottom_cut_overlap)):
            Cylinder(radius=fix_cbore_r,
                     height=fix_cbore_depth + bottom_cut_overlap,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)
        with Locations((hx, hy, fix_cbore_depth)):
            Cylinder(radius=fix_bore_r, height=total_height - fix_cbore_depth,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

    # 5. Spoke bore holes — already represented as rounded window ends

    # 6. Arm / bracket (ADD — restores solid in opening A top region)
    with Locations((0, (arm_y_start+arm_y_end)/2, arm_height/2)):
        Box(arm_x_half*2, arm_y_end-arm_y_start, arm_height,
            align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.ADD)

    # 7. Gussets ×2
    for sx in [+1, -1]:
        with Locations((sx*(gusset_x_inner+gusset_x_outer)/2,
                        (gusset_y_start+gusset_y_end)/2,
                        arm_height/2)):
            Box(gusset_x_outer-gusset_x_inner,
                gusset_y_end-gusset_y_start,
                arm_height,
                align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.ADD)

    # 8. Keyway rect Z=0..81.75
    with Locations((0, (kw_y_inner+kw_y_outer)/2,
                    (kw_rect_top_z - bottom_cut_overlap) / 2)):
        Box(kw_x_half*2, kw_y_outer-kw_y_inner,
            kw_rect_top_z + bottom_cut_overlap,
            align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)

    # 9. Keyway V-groove Z=81.75..98.5
    with BuildSketch(Plane.YZ.offset(0)) as _sk:
        Polygon([(kw_y_inner, kw_rect_top_z),
                 (kw_y_outer, kw_rect_top_z),
                 ((kw_y_inner+kw_y_outer)/2, kw_slope_top_z)], align=None)
    extrude(_sk.sketch, amount=kw_x_half, both=True, mode=Mode.SUBTRACT)

    # 10. Keyway radial bores
    #     Use centered Y-axis tools so the outer r=17 bore runs from the
    #     circumference to the slot face instead of being reversed inward.
    for y0, y1 in [
        (arm_y_start, kw_y_inner),
        (kw_y_outer, rim_radius + 3.0),
    ]:
        with Locations((0, (y0 + y1) / 2, kw_bore_z)):
            with Locations(Rotation(90, 0, 0)):
                Cylinder(radius=kw_bore_r, height=abs(y1 - y0),
                         align=(Align.CENTER, Align.CENTER, Align.CENTER),
                         mode=Mode.SUBTRACT)

    # 11. Side counterbored holes ×2
    for sx in [+1, -1]:
        hx = sx * side_hole_x
        with Locations((hx, 0, side_bore_z1)):
            Cylinder(radius=side_bore_r, height=side_bore_z2-side_bore_z1,
                     align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with Locations((hx, 0, side_bore_z2)):
            add(_side_cbore_d_tool(sx, total_height-side_bore_z2),
                mode=Mode.SUBTRACT)

    # 12. Bottom-surface profile cuts
    #     The central profile is a shallow 40 mm relief. The keyway/bracket-side
    #     profile is a deeper 130 mm cut and is aligned by the small
    #     rectangle matching the existing keyway rectangle.
    add(_profile_cut_tool(
            _bottom_middle_cut_loop(),
            bottom_middle_cut_depth + bottom_cut_overlap,
            z_start=-bottom_cut_overlap,
        ),
        mode=Mode.SUBTRACT)
    for _profile in _bottom_remaining_clean_loops():
        add(_profile_cut_tool(
                _profile,
                bottom_remaining_cut_depth + bottom_cut_overlap,
                z_start=-bottom_cut_overlap,
            ),
            mode=Mode.SUBTRACT)
    add(_bottom_remaining_cut_tool(bottom_remaining_cut_depth + bottom_cut_overlap),
        mode=Mode.SUBTRACT)

# ══════════════════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

result = part.part
bb     = result.bounding_box()

print("=" * 58)
print("  Art3Pulley — build summary")
print("=" * 58)
print(f"  Volume  : {result.volume:>18.4f} mm³")
print(f"  Faces   : {len(result.faces()):>4d}   (STEP: 73)")
print(f"  X span  : {bb.min.X:.1f} → {bb.max.X:.1f}  ({bb.max.X-bb.min.X:.1f} mm)")
print(f"  Y span  : {bb.min.Y:.1f} → {bb.max.Y:.1f}  ({bb.max.Y-bb.min.Y:.1f} mm)")
print(f"  Z span  : {bb.min.Z:.1f} → {bb.max.Z:.1f}  ({bb.max.Z-bb.min.Z:.1f} mm)")
if os.path.exists(REFERENCE_STEP_PATH):
    try:
        _ref_step = import_step(REFERENCE_STEP_PATH)
        _delta = (result.volume - _ref_step.volume) / _ref_step.volume * 100
        print(f"  Ref STEP: {len(_ref_step.faces()):>4d} faces, {_ref_step.volume:>18.4f} mm³")
        print(f"  CAD Δ   : {_delta:>+17.4f} % vs Art3Pulley-faces.step")
    except Exception as _e:
        print(f"  Ref STEP: [failed — {_e}]")
print("=" * 58)

# ══════════════════════════════════════════════════════════════════════════════
#  EXPORT
# ══════════════════════════════════════════════════════════════════════════════

os.makedirs(OUTPUT_DIR, exist_ok=True)

_step_path = _base + ".step"
export_step(result, _step_path)
print(f"STEP exported : {_step_path}")

_stl_path = _base + ".stl"
try:
    try:
        import cadquery as cq
    except ImportError:
        import site
        _user_site = site.getusersitepackages()
        if os.path.exists(_user_site) and _user_site not in sys.path:
            sys.path.append(_user_site)
        import cadquery as cq
    _cq = cq.importers.importStep(_step_path)
    cq.exporters.export(_cq, _stl_path,
                        exportType="STL", tolerance=0.01, angularTolerance=0.1)
    print(f"STL  exported : {_stl_path}  (via CadQuery)")
except ImportError:
    export_stl(result, _stl_path, tolerance=0.01, angular_tolerance=0.1)
    print(f"STL  exported : {_stl_path}")

_repair_stl_watertight(_stl_path)

# ══════════════════════════════════════════════════════════════════════════════
#  INLINE STL VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

_ref_stl = os.path.join(OUTPUT_DIR, "Art3Pulley.stl")

if os.path.exists(_ref_stl):
    try:
        import trimesh, numpy as np

        _ref_raw = trimesh.load(_ref_stl, force="mesh")
        _gen     = trimesh.load(_stl_path, force="mesh")

        _spans_g = _gen.bounds[1] - _gen.bounds[0]
        _spans_r = _ref_raw.bounds[1] - _ref_raw.bounds[0]
        _scale   = round(float(np.median(
                       _spans_g / np.where(_spans_r > 0, _spans_r, 1))) * 4) / 4
        _ref = _ref_raw.copy()
        if abs(_scale - 1.0) > 0.05:
            _ref.apply_scale(_scale)

        _step_vol      = result.volume
        _step_diff_pct = (_gen.volume - _step_vol) / _step_vol * 100
        _ref_diff_pct  = (_gen.volume - _ref.volume) / _ref.volume * 100

        print("\n" + "─" * 58)
        print("  STL Validation")
        print("─" * 58)
        print(f"  Ref STL vol   : {_ref.volume:>18.2f} mm³" +
              (f"  (×{_scale:.2f})" if abs(_scale-1) > 0.05 else ""))
        print(f"  Gen STL vol   : {_gen.volume:>18.2f} mm³")
        print(f"  CAD vol       : {_step_vol:>18.2f} mm³")
        print(f"  Gen vs CAD    : {_step_diff_pct:>+17.4f} %"
              + ("  ✓" if abs(_step_diff_pct) < 1.0 else "  ✗"))
        print(f"  Gen vs Ref    : {_ref_diff_pct:>+17.4f} %  (ref mesh approx)")

        # CAD symmetric difference from STEP/OCP booleans. This avoids STL
        # watertightness problems and compares the actual CAD solids.
        try:
            _ref_cad = import_step(REFERENCE_STEP_PATH)
            _cad_gen_only = result.cut(_ref_cad).volume
            _cad_ref_only = _ref_cad.cut(result).volume
            _cad_union_est = (
                (result.volume + _cad_ref_only)
                + (_ref_cad.volume + _cad_gen_only)
            ) / 2.0
            _cad_sym_pct = (
                (_cad_gen_only + _cad_ref_only) / _cad_union_est * 100
            )
            print(f"  CAD sym-diff  : {_cad_sym_pct:>17.4f} % of union"
                  + ("  ✓" if _cad_sym_pct < 10.0 else "  ✗"))
            print(f"                  gen-only={_cad_gen_only:.2f}, "
                  f"ref-only={_cad_ref_only:.2f} mm³")
        except Exception as _e:
            print(f"  CAD sym-diff  : [failed — {_e}]")

        # STL sym-diff with mesh repair fallback. Trimesh booleans require a mesh
        # to be a valid volume, which is stricter than simply having a volume.
        def _mesh_status(label, mesh):
            return (
                f"{label}: watertight={mesh.is_watertight}, "
                f"winding={mesh.is_winding_consistent}, "
                f"is_volume={mesh.is_volume}"
            )


        def _fix(mesh):
            fixed = mesh.copy()
            fixed.process(validate=True)
            try:
                fixed.remove_duplicate_faces()
            except Exception:
                pass
            try:
                fixed.remove_degenerate_faces()
            except Exception:
                pass
            try:
                fixed.remove_unreferenced_vertices()
            except Exception:
                pass
            try:
                trimesh.repair.fill_holes(fixed)
            except Exception:
                pass
            try:
                trimesh.repair.fix_normals(fixed)
            except Exception:
                pass
            try:
                trimesh.repair.fix_inversion(fixed)
            except Exception:
                pass
            fixed.process(validate=True)
            return fixed


        def _sym_diff(gen_mesh, ref_mesh, check_volume=True):
            d1 = trimesh.boolean.difference(
                [gen_mesh, ref_mesh],
                engine="manifold",
                check_volume=check_volume,
            )
            d2 = trimesh.boolean.difference(
                [ref_mesh, gen_mesh],
                engine="manifold",
                check_volume=check_volume,
            )
            union = trimesh.boolean.union(
                [gen_mesh, ref_mesh],
                engine="manifold",
                check_volume=check_volume,
            )
            return (d1.volume + d2.volume) / union.volume * 100

        try:
            _gw = _fix(_gen)
            _rw = _fix(_ref)
            _note = "  (repaired)" if (
                _mesh_status("gen", _gw) != _mesh_status("gen", _gen)
                or _mesh_status("ref", _rw) != _mesh_status("ref", _ref)
            ) else ""
            if not (_gw.is_volume and _rw.is_volume):
                print("  STL sym-diff  : [skipped — mesh is not a valid boolean volume]")
                print(f"  Mesh status   : {_mesh_status('gen', _gw)}")
                print(f"                  {_mesh_status('ref', _rw)}")
            else:
                _sp = _sym_diff(_gw, _rw, check_volume=True)
                print(f"  STL sym-diff  : {_sp:>17.4f} % of union"
                      + ("  ✓" if _sp < 10.0 else "  ✗") + _note)
        except Exception as _e:
            print(f"  STL sym-diff  : [failed — {_e}]")
            print(f"  Mesh status   : {_mesh_status('gen', _fix(_gen))}")
            print(f"                  {_mesh_status('ref', _fix(_ref))}")
        print("─" * 58)

    except ImportError:
        print("[SKIP] pip install trimesh manifold3d scipy  (same env as this script)")
    except Exception as _e:
        print(f"[WARN] Validation failed: {_e}")
else:
    print(f"[SKIP] Ref STL not found: {_ref_stl}")

# ══════════════════════════════════════════════════════════════════════════════
#  OCP VIEWER
# ══════════════════════════════════════════════════════════════════════════════

print("[debug] viewer disabled")
