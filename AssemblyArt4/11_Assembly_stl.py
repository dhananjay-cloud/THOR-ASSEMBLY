"""
assemble_stl_files.py

Assembles all 10 Thor Art4 parts from STL files into a single assembly.
Uses the transformation data extracted from the Fusion 360 assembly.

Components: 12 instances (10 unique parts, with 2 mirrored copies of
Art4BearingFix and Art4BodyFan).

Note: STL files are mesh-based (triangles only). The assembly is created
by importing each mesh, applying transforms, and exporting the combined
result. For CAD-quality geometry, use assemble_step_files.py instead.

Output: Thor_AssemblyArt4_STL.stl
"""

import os
import math
import numpy as np
from stl import mesh as stlmesh

# ── PATHS ──────────────────────────────────────────────────────────────────
BASE_DIR = "/Users/avajones/Documents/ava_build123d/20260413_assign/1_10_Thor_AssemblyArt4"

# STL file names (all in BASE_DIR)
STL_FILES = {
    "1_BearingFix":         "1_Art4BearingFix_build123d_G_1_9.stl",
    "2_BodyBot":            "2_Art4BodyBot_G_1_18.stl",
    "3_BodyFan":            "3_Art4BodyFan_G_1_7.stl",
    "4_Optodisk":           "4_Art4Optodisk_G_1_13.stl",
    "5_TransmissionColumn": "5_Art4TransmissionColumn_G_1_16.stl",
    "6_BearingPlug":        "6_Art4BearingPlug_G_1_9.stl",
    "7_BearingRing":        "7_Art4BearingRing_G_1_14.stl",
    "8_Body":               "8_Art4Body_G_1_42.stl",
    "9_MotorFix":           "9_Art4MotorFix_G_1_7.stl",
    "10_MotorGear":         "10_Art4MotorGear_G_1_15.stl",
}

# ── ASSEMBLY TRANSFORMS ───────────────────────────────────────────────────
# Format: (part_key, instance_label, (tx, ty, tz), rotation_matrix_3x3)
# Rotation matrix applied directly from Fusion 360 transform data.

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

def transform_mesh(stl_mesh, translation, rot_matrix):
    """Apply 3x3 rotation matrix then translation to an STL mesh (in-place)."""
    tx, ty, tz = translation
    rot = np.array(rot_matrix)

    # Apply rotation to all vertices and normals
    for i in range(len(stl_mesh.vectors)):
        for j in range(3):
            stl_mesh.vectors[i][j] = rot @ stl_mesh.vectors[i][j]
        stl_mesh.normals[i] = rot @ stl_mesh.normals[i]

    # Apply translation
    stl_mesh.vectors += np.array([tx, ty, tz])

    return stl_mesh


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("  Thor AssemblyArt4 — STL Assembly Script")
    print("=" * 65)

    # Load all unique parts
    parts = {}
    for key, filename in STL_FILES.items():
        filepath = os.path.join(BASE_DIR, filename)
        if os.path.exists(filepath):
            parts[key] = filepath
            print(f"  Found {filename}")
        else:
            print(f"  ❌ Missing: {filename}")

    # Place each instance
    all_meshes = []

    for part_key, label, translation, rot_matrix in ASSEMBLY:
        if part_key not in parts:
            print(f"  ⚠️  Skipping {label} — part not found.")
            continue

        # Load a fresh copy of the mesh
        m = stlmesh.Mesh.from_file(parts[part_key])
        transform_mesh(m, translation, rot_matrix)

        all_meshes.append(m)
        print(f"  ✓ Placed {label} at ({translation[0]:.1f}, {translation[1]:.1f}, {translation[2]:.1f})")

    print(f"\n  Total instances placed: {len(all_meshes)}")

    # Combine all meshes into one
    if all_meshes:
        total_faces = sum(len(m.vectors) for m in all_meshes)
        combined = stlmesh.Mesh(np.zeros(total_faces, dtype=stlmesh.Mesh.dtype))

        offset = 0
        for m in all_meshes:
            n = len(m.vectors)
            combined.vectors[offset:offset + n] = m.vectors
            combined.normals[offset:offset + n] = m.normals
            offset += n

        # Export combined STL
        output_path = os.path.join(BASE_DIR, "Thor_AssemblyArt4_STL.stl")
        combined.save(output_path)
        stl_kb = os.path.getsize(output_path) / 1024
        print(f"\n  ✓ Saved: Thor_AssemblyArt4_STL.stl ({stl_kb:.1f} KB)")
        print(f"    Total triangles: {total_faces:,}")

        # Display in OCP viewer by re-importing the saved STL
        try:
            from build123d import import_stl, Solid
            from ocp_vscode import show, set_port

            print("\n  Loading assembly STL into OCP viewer...")
            assembly_solid = import_stl(output_path)
            set_port(3939)
            show([assembly_solid], names=["Thor_AssemblyArt4_STL"])
        except Exception as e:
            print(f"  ⚠️  OCP viewer display failed: {e}")
            print("     (STL file was saved successfully — open it manually)")

    print(f"\n{'='*65}")
    print("  ASSEMBLY COMPLETE")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()