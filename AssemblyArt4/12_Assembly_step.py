"""
assemble_step_files.py

Assembles all 10 Thor Art4 parts from STEP files into a single assembly.
Uses the transformation data extracted from the Fusion 360 assembly.

Components: 12 instances (10 unique parts, with 2 mirrored copies of
Art4BearingFix and Art4BodyFan).

Output: Thor_AssemblyArt4.step + Thor_AssemblyArt4.stl
"""

import os
import math
from build123d import *
from ocp_vscode import show, set_port

# ── PATHS ──────────────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/1_10_Thor_AssemblyArt4"

# STEP file names (all in BASE_DIR)
STEP_FILES = {
    "1_BearingFix":         "1_Art4BearingFix_build123d_G_1_9.step",
    "2_BodyBot":            "2_Art4BodyBot_G_1_18.step",
    "3_BodyFan":            "3_Art4BodyFan_G_1_7.step",
    "4_Optodisk":           "4_Art4Optodisk_G_1_13.step",
    "5_TransmissionColumn": "5_Art4TransmissionColumn_G_1_16.step",
    "6_BearingPlug":        "6_Art4BearingPlug_G_1_9.step",
    "7_BearingRing":        "7_Art4BearingRing_G_1_14.step",
    "8_Body":               "8_Art4Body_G_1_42.step",
    "9_MotorFix":           "9_Art4MotorFix_G_1_7.step",
    "10_MotorGear":         "10_Art4MotorGear_G_1_15.step",
}

# ── ASSEMBLY TRANSFORMS ───────────────────────────────────────────────────
# Extracted from Fusion 360 assembly via API script.
# Format: (part_key, instance_label, (tx, ty, tz), rotation_matrix_3x3)
# Rotation matrix is applied directly — no Euler angle conversion needed.

ASSEMBLY = [
    ("8_Body", "Art4Body",
     (0.0, 0.0, -189.5),
     [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),

    ("2_BodyBot", "Art4BodyBot",
     (0.0, 0.0, -194.0),
     [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),

    ("9_MotorFix", "Art4MotorFix",
     (0.0, 0.0, -189.5),
     [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),

    ("7_BearingRing", "Art4BearingRing",
     (0.0, 0.0, -205.84),
     [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),

    ("5_TransmissionColumn", "Art4TransmissionColumn",
     (0.0, 0.0, -270.0),
     [[0.929785, -0.368104, 0], [0.368104, 0.929785, 0], [0, 0, 1]]),

    ("10_MotorGear", "Art4MotorGear",
     (0.0, 0.0, -184.0),
     [[0.929785, -0.368104, 0], [0.368104, 0.929785, 0], [0, 0, 1]]),

    ("4_Optodisk", "Art4Optodisk",
     (0.0, 0.0, -206.0),
     [[-0.918676, 0.395011, 0], [0.395011, 0.918676, 0], [0, 0, -1]]),

    ("6_BearingPlug", "Art4BearingPlug",
     (-35.857, 0.0, -200.84),
     [[-1, 0, 0], [0, 1, 0], [0, 0, -1]]),

    ("3_BodyFan", "Art4BodyFan_Left",
     (-66.001, 0.0, -189.5),
     [[1, 0, 0], [0, 1, 0], [0, 0, 1]]),

    ("3_BodyFan", "Art4BodyFan_Right",
     (66.0, 0.0, -189.5),
     [[-1, 0, 0], [0, -1, 0], [0, 0, 1]]),

    ("1_BearingFix", "Art4BearingFix_Left",
     (-51.0, 0.0, -89.5),
     [[0, 0, -1], [1, 0, 0], [0, -1, 0]]),

    ("1_BearingFix", "Art4BearingFix_Right",
     (51.0, 0.0, -89.5),
     [[0, 0, 1], [-1, 0, 0], [0, -1, 0]]),
]


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def load_step(filepath):
    """Import a STEP file and return the first Solid."""
    shapes = import_step(filepath)
    if isinstance(shapes, (list, tuple)):
        # Find largest solid
        solids = [s for s in shapes if isinstance(s, Solid)]
        if solids:
            return max(solids, key=lambda s: s.volume)
        return shapes[0] if shapes else None
    return shapes


def apply_transform(solid, translation, rot_matrix):
    """Apply a 3x3 rotation matrix + translation to a solid using OCP gp_Trsf."""
    from OCP.gp import gp_Trsf, gp_Mat, gp_XYZ, gp_Vec as ocp_Vec
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

    tx, ty, tz = translation
    r = rot_matrix

    trsf = gp_Trsf()
    mat = gp_Mat(
        r[0][0], r[0][1], r[0][2],
        r[1][0], r[1][1], r[1][2],
        r[2][0], r[2][1], r[2][2]
    )
    trsf.SetValues(
        r[0][0], r[0][1], r[0][2], tx,
        r[1][0], r[1][1], r[1][2], ty,
        r[2][0], r[2][1], r[2][2], tz
    )

    transformed = BRepBuilderAPI_Transform(solid.wrapped, trsf, True)
    return Solid(transformed.Shape())


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("  Thor AssemblyArt4 — STEP Assembly Script")
    print("=" * 65)

    # Load all unique parts
    parts = {}
    for key, filename in STEP_FILES.items():
        filepath = os.path.join(BASE_DIR, filename)
        if os.path.exists(filepath):
            print(f"  Loading {filename}...")
            parts[key] = load_step(filepath)
        else:
            print(f"  ❌ Missing: {filename}")

    # Place each instance
    placed = []
    labels = []

    for part_key, label, translation, rot_matrix in ASSEMBLY:
        if part_key not in parts:
            print(f"  ⚠️  Skipping {label} — part not loaded.")
            continue

        # Make a copy so we don't modify the original
        solid = Solid(parts[part_key].wrapped)
        transformed = apply_transform(solid, translation, rot_matrix)

        placed.append(transformed)
        labels.append(label)
        print(f"  ✓ Placed {label} at ({translation[0]:.1f}, {translation[1]:.1f}, {translation[2]:.1f})")

    print(f"\n  Total instances placed: {len(placed)}")

    # Export assembly
    if placed:
        # Export as compound STEP
        assembly_step = os.path.join(BASE_DIR, "Thor_AssemblyArt4_STEP.step")
        try:
            assembly_compound = Compound(placed)
            export_step(assembly_compound, assembly_step)
            step_kb = os.path.getsize(assembly_step) / 1024
            print(f"  ✓ STEP saved: Thor_AssemblyArt4_STEP.step ({step_kb:.1f} KB)")
        except Exception as e:
            print(f"  ❌ STEP export failed: {e}")

        # Export as STL too
        assembly_stl = os.path.join(BASE_DIR, "Thor_AssemblyArt4_STEP.stl")
        try:
            export_stl(assembly_compound, assembly_stl, tolerance=0.01, angular_tolerance=0.1)
            stl_kb = os.path.getsize(assembly_stl) / 1024
            print(f"  ✓ STL saved:  Thor_AssemblyArt4_STEP.stl ({stl_kb:.1f} KB)")
        except Exception as e:
            print(f"  ❌ STL export failed: {e}")

    print(f"\n{'='*65}")
    print("  ASSEMBLY COMPLETE")
    print(f"{'='*65}")

    # Display in OCP viewer
    print("\nDisplaying in OCP viewer on port 3939...")
    set_port(3939)
    show(placed, names=labels)


if __name__ == "__main__":
    main()