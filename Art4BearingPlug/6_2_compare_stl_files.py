"""
STL Comparison Script  (with % error reporting)
================================================
Compares two STL files (build123d vs Fusion 360 original) and reports:
  1. Volume comparison          → absolute diff + % error vs original
  2. Symmetric difference       → absolute + % of original volume
  3. Bounding box comparison    → absolute diff + % error per axis
  4. Summary scorecard          → overall quality rating

Usage:
  python 4_compare_stl_files.py
"""

import os
import sys
import numpy as np
from stl import mesh
import trimesh
import trimesh.boolean as tb
from datetime import datetime

# ── File paths ───────────────────────────────────────────────────────────────
BASE_DIR      = "/Users/avajones/Documents/ava_build123d/20260413_assign/6_Art4BearingPlug"
BUILD123D_STL = os.path.join(BASE_DIR, "6_Art4BearingPlug_G_1_9.stl")
FUSION_STL    = os.path.join(BASE_DIR, "6_Art4BearingPlug_original.stl") # <-- Updated filename!
REPORT_TXT    = os.path.join(BASE_DIR, "6_Art4BearingPlug_original_build123d_vs_original_G_1_9.txt")

# ── Grading thresholds ───────────────────────────────────────────────────────
VOL_PCT_EXCELLENT  = 1.0   # %
VOL_PCT_GOOD       = 3.0
VOL_PCT_ACCEPTABLE = 5.0

SYM_PCT_EXCELLENT  = 2.0
SYM_PCT_GOOD       = 5.0
SYM_PCT_ACCEPTABLE = 10.0

BB_TOL_MM = 0.1            # mm per bounding box axis

# ── Tee: write to terminal AND file simultaneously ───────────────────────────
class Tee:
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log      = open(filepath, "w")
    def write(self, msg):
        self.terminal.write(msg)
        self.log.write(msg)
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    def close(self):
        self.log.close()

# ── Helpers ──────────────────────────────────────────────────────────────────
def pct_err(diff, reference):
    if reference == 0:
        return float('inf')
    return abs(diff) / abs(reference) * 100.0

def grade(p, exc, good, acc):
    if p <= exc:  return "🟢 EXCELLENT"
    if p <= good: return "🟡 GOOD"
    if p <= acc:  return "🟠 ACCEPTABLE"
    return            "🔴 POOR"

def sep(c='='):
    print(f"\n  {c*57}")

# ════════════════════════════════════════════════════════════════════════════
# PART 1 — Mesh info
# ════════════════════════════════════════════════════════════════════════════
def load_and_inspect(filepath, label):
    m = mesh.Mesh.from_file(filepath)
    volume, cog, _ = m.get_mass_properties()
    sep()
    print(f"  {label}")
    sep()
    print(f"  File           : {os.path.basename(filepath)}")
    print(f"  Triangles      : {len(m.vectors):,}  (more = finer mesh = less approx error)")
    print(f"  Volume         : {volume:.4f} mm³")
    print(f"  Center of mass : ({cog[0]:.3f}, {cog[1]:.3f}, {cog[2]:.3f}) mm")
    print(f"  X range        : {m.vectors[:,:,0].min():.4f} → {m.vectors[:,:,0].max():.4f} mm")
    print(f"  Y range        : {m.vectors[:,:,1].min():.4f} → {m.vectors[:,:,1].max():.4f} mm")
    print(f"  Z range        : {m.vectors[:,:,2].min():.4f} → {m.vectors[:,:,2].max():.4f} mm")
    return volume

# ════════════════════════════════════════════════════════════════════════════
# PART 2 — Volume comparison with % error
# ════════════════════════════════════════════════════════════════════════════
def volumetric_difference(vol_b123d, vol_fusion):
    diff   = vol_b123d - vol_fusion
    p      = pct_err(diff, vol_fusion)
    rating = grade(p, VOL_PCT_EXCELLENT, VOL_PCT_GOOD, VOL_PCT_ACCEPTABLE)

    sep()
    print(f"  VOLUME COMPARISON")
    sep()
    print(f"  {'Metric':<30} {'Value':>15}  {'Unit'}")
    print(f"  {'-'*57}")
    print(f"  {'Build123d volume':<30} {vol_b123d:>15.4f}  mm³")
    print(f"  {'Fusion volume (reference)':<30} {vol_fusion:>15.4f}  mm³")
    print(f"  {'Absolute difference':<30} {diff:>+15.4f}  mm³  ({'build123d larger' if diff>0 else 'build123d smaller'})")
    print(f"  {'% error vs original':<30} {p:>15.4f}  %")
    print(f"  {'Rating':<30} {rating}")
    return p

# ════════════════════════════════════════════════════════════════════════════
# PART 3 — Symmetric difference with % error
# ════════════════════════════════════════════════════════════════════════════
def symmetric_difference(file_a, file_b, vol_fusion):
    sep()
    print(f"  SYMMETRIC DIFFERENCE  (spatial overlap quality)")
    sep()

    mesh_a = trimesh.load(file_a)
    mesh_b = trimesh.load(file_b)

    print(f"  Mesh A watertight : {mesh_a.is_watertight}")
    print(f"  Mesh B watertight : {mesh_b.is_watertight}")

    try:
        inter        = tb.intersection([mesh_a, mesh_b], engine='manifold')
        vol_a        = mesh_a.volume
        vol_b        = mesh_b.volume
        vol_inter    = inter.volume
        sym_vol      = vol_a + vol_b - 2 * vol_inter
        overlap_pct  = vol_inter / vol_b * 100.0
        sym_p        = pct_err(sym_vol, vol_fusion)
        rating       = grade(sym_p, SYM_PCT_EXCELLENT, SYM_PCT_GOOD, SYM_PCT_ACCEPTABLE)

        print(f"")
        print(f"  {'Metric':<35} {'Value':>12}  Unit")
        print(f"  {'-'*57}")
        print(f"  {'Volume A (Build123d)':<35} {vol_a:>12.4f}  mm³")
        print(f"  {'Volume B (Fusion original)':<35} {vol_b:>12.4f}  mm³")
        print(f"  {'Intersection volume':<35} {vol_inter:>12.4f}  mm³")
        print(f"  {'Overlap coverage (inter/Fusion)':<35} {overlap_pct:>12.4f}  %")
        print(f"  {'-'*57}")
        print(f"  {'Symmetric diff volume':<35} {sym_vol:>12.4f}  mm³")
        print(f"  {'Sym diff % of Fusion volume':<35} {sym_p:>12.4f}  %")
        print(f"  {'Rating':<35} {rating}")
        return sym_p, overlap_pct

    except Exception as e:
        print(f"  ❌ Boolean operation failed: {e}")
        return None, None

# ════════════════════════════════════════════════════════════════════════════
# PART 4 — Bounding box with % error per axis
# ════════════════════════════════════════════════════════════════════════════
def bounding_box_check(file_a, file_b):
    mesh_a = trimesh.load(file_a)
    mesh_b = trimesh.load(file_b)
    ba     = mesh_a.bounds
    bb     = mesh_b.bounds

    sep()
    print(f"  BOUNDING BOX COMPARISON  (tolerance ±{BB_TOL_MM} mm per axis)")
    sep()
    print(f"  {'Axis':<6} {'Build123d':>12} {'Fusion':>12} {'Diff mm':>10} {'% err':>8}  Status")
    print(f"  {'-'*65}")

    axes   = ['X min','X max','Y min','Y max','Z min','Z max']
    vals_a = [ba[0][0], ba[1][0], ba[0][1], ba[1][1], ba[0][2], ba[1][2]]
    vals_b = [bb[0][0], bb[1][0], bb[0][1], bb[1][1], bb[0][2], bb[1][2]]
    spans  = [bb[1][0]-bb[0][0], bb[1][0]-bb[0][0],
              bb[1][1]-bb[0][1], bb[1][1]-bb[0][1],
              bb[1][2]-bb[0][2], bb[1][2]-bb[0][2]]

    all_pass = True
    for axis, va, vb, span in zip(axes, vals_a, vals_b, spans):
        diff     = va - vb
        p        = pct_err(diff, span) if span != 0 else 0.0
        passes   = abs(diff) <= BB_TOL_MM
        all_pass = all_pass and passes
        icon     = "✅ pass" if passes else "❌ fail"
        print(f"  {axis:<6} {va:>12.4f} {vb:>12.4f} {diff:>+10.4f} {p:>7.3f}%  {icon}")

    print(f"\n  Overall bounding box : {'✅ PASS' if all_pass else '❌ FAIL'}")
    return all_pass

# ════════════════════════════════════════════════════════════════════════════
# PART 5 — Summary scorecard
# ════════════════════════════════════════════════════════════════════════════
def print_summary(vol_p, sym_p, overlap_p, bb_pass):
    sep('█')
    print(f"  SUMMARY SCORECARD")
    sep('█')
    print(f"  {'Check':<35} {'Score':>10}   Rating")
    print(f"  {'-'*65}")
    print(f"  {'Volume % error':<35} {vol_p:>9.3f}%   {grade(vol_p, VOL_PCT_EXCELLENT, VOL_PCT_GOOD, VOL_PCT_ACCEPTABLE)}")
    print(f"  {'Symmetric diff % error':<35} {sym_p:>9.3f}%   {grade(sym_p, SYM_PCT_EXCELLENT, SYM_PCT_GOOD, SYM_PCT_ACCEPTABLE)}")
    print(f"  {'Overlap coverage':<35} {overlap_p:>9.2f}%   {'🟢 EXCELLENT' if overlap_p>=97 else '🟡 GOOD' if overlap_p>=94 else '🟠 ACCEPTABLE'}")
    print(f"  {'Bounding box':<35} {'PASS' if bb_pass else 'FAIL':>10}   {'✅' if bb_pass else '❌'}")
    sep('█')

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":

    tee = Tee(REPORT_TXT)
    sys.stdout = tee

    print("\n" + "█"*59)
    print("  STL COMPARISON: Build123d  vs  Fusion 360 Original")
    print(f"  Run time  : {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    print("█"*59)
    print(f"  Build123d : {os.path.basename(BUILD123D_STL)}")
    print(f"  Original  : {os.path.basename(FUSION_STL)}")
    print(f"  Report    : {os.path.basename(REPORT_TXT)}")

    vol_b123d  = load_and_inspect(BUILD123D_STL, "Build123d STL")
    vol_fusion = load_and_inspect(FUSION_STL,    "Fusion 360 Original STL")

    vol_p              = volumetric_difference(vol_b123d, vol_fusion)
    sym_p, overlap_p   = symmetric_difference(BUILD123D_STL, FUSION_STL, vol_fusion)
    bb_pass            = bounding_box_check(BUILD123D_STL, FUSION_STL)

    if sym_p is not None:
        print_summary(vol_p, sym_p, overlap_p, bb_pass)

    print(f"\n  Report saved → {REPORT_TXT}\n")

    sys.stdout = tee.terminal
    tee.close()
    print(f"✓ Report written → {REPORT_TXT}")