"""
0_preprocess_csvs.py

This script:
1. Scans all CSV files in csv_data_1_Art4BearingFix folder.
2. Checks if the shape has ALREADY been merged in csv_merged. If yes, skips it
   (incremental mode — safe to re-run after adding new shapes).
3. Identifies split files (e.g., S25_1, S25_2) and merges them into S25.
4. Removes geometry-aware duplicate rows:
     - Points:    A == A                     (same single vertex)
     - Lines:     A→B  ==  B→A              (direction doesn't matter)
     - Triangles: A,B,C == B,C,A == C,A,B   (vertex rotation doesn't matter)
     All cases: only the first occurrence is kept.
5. Re-numbers the Steps column sequentially (1, 2, 3, ...).
6. Saves cleaned/merged files into csv_merged (only new shapes written).
7. Logs execution summary to a text file.

Bug fixes vs previous version:
  - Draw Type normalised: "triangular_face_1", "triangular_face_60" etc. all
    collapse to "triangular" before key comparison, so row 1 (A,B,C) and
    row 60 (A,B,C) are correctly detected as duplicates.
  - NA check hardened: a cell is treated as "missing" if it is blank (""),
    whitespace-only, or the literal string "NA" (case-insensitive). Prevents
    a 2-point line being mistaken for a triangle.
  - Point geometry support: rows where only P1 is present (P2 and P3 are NA)
    are now handled correctly instead of crashing with a float conversion error.
"""

import os
import csv
import re
from collections import defaultdict
from datetime import datetime

# ── PATHS ──
BASE_DIR   = "/Users/avajones/Documents/ava_build123d/20260413_assign/5_Art4TransmissionColumn"
INPUT_DIR  = os.path.join(BASE_DIR, "csv_data_5_Art4TransmissionColumn")
OUTPUT_DIR = os.path.join(BASE_DIR, "csv_merged")

HEADER = ["Steps", "Draw Type", "X1", "Y1", "Z1", "X2", "Y2", "Z2", "X3", "Y3", "Z3"]

# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def extract_shape_info(filename):
    name = filename.replace("Fusion_Coordinates_", "").replace(".csv", "")

    match_sub = re.match(r'^S(\d+)_(\d+)$', name)
    if match_sub:
        return f"S{match_sub.group(1)}", int(match_sub.group(2))

    match_underscore = re.match(r'^S_(\d+)$', name)
    if match_underscore:
        return f"S{match_underscore.group(1)}", 0

    match_simple = re.match(r'^S(\d+)$', name)
    if match_simple:
        return f"S{match_simple.group(1)}", 0

    return name, 0


def read_csv_rows(filepath):
    rows = []
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if row and len(row) >= 11:
                rows.append(row)
    return rows


def is_missing(cell):
    """
    True if a cell should be treated as "no value".
    Handles: empty string, whitespace-only, or the literal "NA" (any case).
    """
    return cell.strip() == "" or cell.strip().upper() == "NA"


def normalize_draw_type(raw):
    """
    Collapse numbered draw-type labels down to their base category so that
    "triangular_face_1" and "triangular_face_60" both become "triangular",
    and any future variants (e.g. "quad_face_3") are similarly normalised.

    Rule: strip everything from the last underscore-followed-by-digits onwards,
    then strip any trailing underscore.
    """
    normalised = re.sub(r'_\d+$', '', raw.strip().lower()).rstrip('_')
    return normalised  # e.g. "triangular_face", "line"


def geometry_key(row):
    """
    Build a geometry-normalised key for duplicate detection.

    Row layout (indices):
        0    = Steps        (ignored for comparison)
        1    = Draw Type    (normalised — numbers stripped)
        2–4  = X1, Y1, Z1  (p1)
        5–7  = X2, Y2, Z2  (p2, or "NA" / blank for points)
        8–10 = X3, Y3, Z3  (p3, or "NA" / blank when not a triangle)

    Rules:
      - Point (p2 missing): just p1          so duplicate points match
      - Line  (p3 missing): sort(p1, p2)     so A→B  == B→A
      - Triangle (p3 present): sort(p1,p2,p3) so A,B,C == B,C,A == C,A,B
    """
    draw_type = normalize_draw_type(row[1])

    def pt(x, y, z):
        # Round to 6 dp to absorb tiny floating-point noise from Fusion export
        return (round(float(x), 6), round(float(y), 6), round(float(z), 6))

    p1 = pt(row[2], row[3], row[4])

    has_p2 = not is_missing(row[5])
    has_p3 = not is_missing(row[8])

    if has_p3:
        p2 = pt(row[5], row[6], row[7])
        p3 = pt(row[8], row[9], row[10])
        # Sort all 3 vertices so any winding order / rotation matches
        verts = tuple(sorted([p1, p2, p3]))
        return (draw_type, "tri", verts)
    elif has_p2:
        p2 = pt(row[5], row[6], row[7])
        # Sort the 2 endpoints so direction doesn't matter
        endpoints = tuple(sorted([p1, p2]))
        return (draw_type, "line", endpoints)
    else:
        # Single point — only P1 is present
        return (draw_type, "point", p1)


def remove_duplicates(rows):
    seen       = set()
    unique     = []
    duplicates = []
    for row in rows:
        key = geometry_key(row)
        if key not in seen:
            seen.add(key)
            unique.append(row)
        else:
            duplicates.append(row)
    return unique, duplicates


def renumber_steps(rows):
    for i, row in enumerate(rows):
        row[0] = str(i + 1)
    return rows


def write_csv(filepath, rows):
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow(row)


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    shape_files = defaultdict(list)

    log_output = []

    def log(message):
        print(message)
        log_output.append(message)

    log("=" * 60)
    log("0_preprocess_csvs.py  Execution Log")
    log(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    csv_files = [
        f for f in os.listdir(INPUT_DIR)
        if f.endswith(".csv") and f.startswith("Fusion_Coordinates_")
    ]
    csv_files.sort()

    log(f"\nFound {len(csv_files)} CSV file(s) in input folder.\n")

    for filename in csv_files:
        filepath = os.path.join(INPUT_DIR, filename)
        base_shape, sub_num = extract_shape_info(filename)
        shape_files[base_shape].append((sub_num, filepath, filename))

    total_written = 0
    total_skipped = 0
    total_dupes   = 0

    sorted_shapes = sorted(
        shape_files.keys(),
        key=lambda s: int(re.findall(r'\d+', s)[0]) if re.findall(r'\d+', s) else 0
    )

    for shape_name in sorted_shapes:
        output_filename = f"Fusion_Coordinates_{shape_name}.csv"
        output_path     = os.path.join(OUTPUT_DIR, output_filename)

        # ── INCREMENTAL SKIP ─────────────────────────────────────────────
        # Shape was already verified and merged → leave it untouched.
        # To force a reprocess: delete that file from csv_merged and re-run.
        if os.path.exists(output_path):
            log(f"SKIPPED  {shape_name}: already in csv_merged — not reprocessed.")
            total_skipped += 1
            continue

        # ── NEW SHAPE: merge split files if any, then clean ──────────────
        files_info = sorted(shape_files[shape_name], key=lambda x: x[0])

        all_rows     = []
        source_files = []
        for sub_num, filepath, filename in files_info:
            rows = read_csv_rows(filepath)
            all_rows.extend(rows)
            source_files.append(filename)

        unique_rows, dupes = remove_duplicates(all_rows)
        n_dupes      = len(dupes)
        total_dupes += n_dupes

        unique_rows = renumber_steps(unique_rows)
        write_csv(output_path, unique_rows)
        total_written += 1

        # ── Log line ─────────────────────────────────────────────────────
        dup_note = f"  [{n_dupes} duplicate(s) removed]" if n_dupes else ""

        if len(files_info) > 1:
            log(f"MERGED   {shape_name}: {len(files_info)} files → {output_filename}{dup_note}")
        else:
            log(f"WROTE    {shape_name}: {source_files[0]} → {output_filename}{dup_note}")

        if dupes:
            tri_dupes   = [r for r in dupes if not is_missing(r[8])]
            line_dupes  = [r for r in dupes if is_missing(r[8]) and not is_missing(r[5])]
            point_dupes = [r for r in dupes if is_missing(r[5])]
            if tri_dupes:
                log(f"           ↳ {len(tri_dupes)} triangle duplicate(s) "
                    f"(same 3 vertices, any winding order)")
            if line_dupes:
                log(f"           ↳ {len(line_dupes)} line duplicate(s) "
                    f"(same 2 endpoints, any direction)")
            if point_dupes:
                log(f"           ↳ {len(point_dupes)} point duplicate(s) "
                    f"(same single vertex)")

    # ── Summary ──────────────────────────────────────────────────────────
    log(f"\n{'='*60}")
    log("SUMMARY")
    log(f"{'='*60}")
    log(f"  Shapes skipped (already merged) : {total_skipped}")
    log(f"  New shapes written              : {total_written}")
    log(f"  Duplicate rows removed (total)  : {total_dupes}")
    log(f"{'='*60}")

    # ── Save Log ─────────────────────────────────────────────────────────
    log_filename = "0_preprocess_csvs_summary.txt"
    log_filepath = os.path.join(BASE_DIR, log_filename)
    with open(log_filepath, "w") as lf:
        lf.write("\n".join(log_output))

    print(f"\n📄 Summary saved to: {log_filename}")


if __name__ == "__main__":
    main()