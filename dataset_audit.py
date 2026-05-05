"""
dataset_audit.py — Indie Dietyy Phase 0
Healthcare-grade data quality audit for all 28 state CSV files.
Parts: A (Structural), B (Nutritional Integrity), C (Clinical Distribution), D (Auto-Correction)
"""

import os
import sys

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import re
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from datetime import datetime

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR   = Path("datasets")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

STANDARD_COLUMNS = {
    "meal name":               "meal_name",
    "meal type":               "meal_type",
    "diet type":               "diet_type",
    "meat type":               "meat_type",
    "calories":                "calories",
    "protein (g)":             "protein_g",
    "protein(g)":              "protein_g",
    "carbs (g)":               "carbs_g",
    "carbs(g)":                "carbs_g",
    "fat (g)":                 "fat_g",
    "fat(g)":                  "fat_g",
    "fiber (g)":               "fiber_g",
    "fiber(g)":                "fiber_g",
    "glycemic index":          "glycemic_index",
    "sodium level":            "sodium_level",
    "cholesterol impact":      "cholesterol_impact",
    "allergens":               "allergens",
    "base ingredients":        "base_ingredients",
    "instructions":            "instructions",
    "exercise recommendation": "exercise_recommendation",
    "medical warning":         "medical_warning",
}

ALLERGEN_INGREDIENTS = {
    "peanut":  ["peanut", "groundnut"],
    "dairy":   ["milk", "paneer", "curd", "yogurt", "ghee", "cheese", "butter", "cream"],
    "gluten":  ["wheat", "maida", "atta", "bread", "roti", "chapati", "semolina", "suji"],
    "egg":     ["egg"],
    "fish":    ["fish", "tuna", "salmon", "mackerel", "sardine", "hilsa", "rohu", "catla"],
    "nut":     ["almond", "cashew", "walnut", "pistachio", "hazelnut"],
}

RICE_SUGAR_KEYWORDS   = ["rice", "sugar", "jaggery", "sweet", "dessert", "kheer", "halwa", "ladoo"]
HIGH_FIBER_VEGETABLES = ["spinach", "methi", "kale", "broccoli", "cabbage", "beans", "lentil", "dal"]
HIGH_SODIUM_INGREDIENTS = ["pickle", "achaar", "papad", "pappad", "soy sauce", "processed"]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def extract_state_name(filepath: Path) -> str:
    """Extract clean state name from messy filename."""
    name = filepath.stem
    name = re.sub(r"[\(\d\)]+", "", name)
    name = re.sub(r"_diet_dataset.*$", "", name)
    return name.strip("_ ").replace("_", " ").title()


def standardise_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Rename columns to snake_case standard. Returns (df, list_of_changes)."""
    changes = []
    rename_map = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in STANDARD_COLUMNS and col != STANDARD_COLUMNS[key]:
            rename_map[col] = STANDARD_COLUMNS[key]
            changes.append(f"  '{col}' → '{STANDARD_COLUMNS[key]}'")
        elif key in STANDARD_COLUMNS:
            rename_map[col] = STANDARD_COLUMNS[key]
    df.rename(columns=rename_map, inplace=True)
    return df, changes


def standardise_text(df: pd.DataFrame) -> pd.DataFrame:
    """Title-case all categorical text columns."""
    cat_cols = ["meal_type", "diet_type", "glycemic_index", "sodium_level", "cholesterol_impact"]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
    return df


def load_csv(filepath: Path) -> pd.DataFrame:
    """Load CSV with encoding fallback."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(filepath, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {filepath.name}")


def ingredients_contain(ingredients_str: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in an ingredients string."""
    if pd.isna(ingredients_str):
        return False
    s = str(ingredients_str).lower()
    return any(kw in s for kw in keywords)


# ══════════════════════════════════════════════════════════════════════════════
# PART A — STRUCTURAL AUDIT
# ══════════════════════════════════════════════════════════════════════════════

def audit_structural(filepath: Path) -> dict:
    """Run structural audit on one CSV file."""
    df = load_csv(filepath)
    state = extract_state_name(filepath)

    df, col_changes = standardise_columns(df)

    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    duplicates = df.duplicated().sum()

    return {
        "state":       state,
        "filepath":    str(filepath),
        "rows":        len(df),
        "columns":     list(df.columns),
        "dtypes":      df.dtypes.astype(str).to_dict(),
        "missing":     missing.to_dict(),
        "missing_pct": missing_pct.to_dict(),
        "duplicates":  int(duplicates),
        "col_changes": col_changes,
        "df":          df,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART B — NUTRITIONAL INTEGRITY AUDIT
# ══════════════════════════════════════════════════════════════════════════════

def audit_nutritional(df: pd.DataFrame, state: str) -> dict:
    """Run all nutritional sanity checks on a state dataframe."""
    issues = defaultdict(list)

    num_cols = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5 — Caloric plausibility
    if "calories" in df.columns:
        low_cal   = df[df["calories"] < 30]
        high_cal  = df[df["calories"] > 1200]
        empty_row = df.query("calories == 0 and protein_g == 0 and carbs_g == 0") \
                      if all(c in df.columns for c in ["calories","protein_g","carbs_g"]) \
                      else pd.DataFrame()
        issues["low_calorie_meals"]  = int(len(low_cal))
        issues["high_calorie_meals"] = int(len(high_cal))
        issues["empty_rows"]         = int(len(empty_row))

    # 6 — Macro math validation
    macro_cols = ["calories", "protein_g", "carbs_g", "fat_g"]
    macro_fails = 0
    if all(c in df.columns for c in macro_cols):
        expected = (df["protein_g"] * 4) + (df["carbs_g"] * 4) + (df["fat_g"] * 9)
        actual   = df["calories"]
        deviation = ((actual - expected).abs() / expected.replace(0, np.nan)) * 100
        macro_fails = int((deviation > 15).sum())
    issues["macro_math_failures"] = macro_fails

    # 7 — Protein sanity
    if "protein_g" in df.columns:
        issues["high_protein_meals"] = int((df["protein_g"] > 60).sum())

    # 8 — Fiber sanity
    if "fiber_g" in df.columns:
        issues["high_fiber_meals"] = int((df["fiber_g"] > 30).sum())

    # 9 — GI consistency
    gi_issues = 0
    if all(c in df.columns for c in ["glycemic_index", "meal_name", "base_ingredients"]):
        for _, row in df.iterrows():
            gi  = str(row.get("glycemic_index","")).strip().lower()
            ing = str(row.get("base_ingredients","")).lower()
            name = str(row.get("meal_name","")).lower()
            if gi == "low" and any(k in name or k in ing for k in RICE_SUGAR_KEYWORDS):
                gi_issues += 1
            if gi == "high" and any(k in ing for k in HIGH_FIBER_VEGETABLES):
                gi_issues += 1
    issues["gi_consistency_issues"] = gi_issues

    # 10 — Sodium consistency
    sodium_issues = 0
    if all(c in df.columns for c in ["sodium_level", "base_ingredients"]):
        mask = df["sodium_level"].str.lower().eq("low")
        for ing in df.loc[mask, "base_ingredients"].fillna(""):
            if any(k in str(ing).lower() for k in HIGH_SODIUM_INGREDIENTS):
                sodium_issues += 1
    issues["sodium_consistency_issues"] = sodium_issues

    # 11 — Allergen coverage
    allergen_empty = 0
    allergen_blind = defaultdict(int)
    if "allergens" in df.columns and "base_ingredients" in df.columns:
        allergen_empty = int(df["allergens"].isna().sum() + (df["allergens"] == "").sum())
        for allergen, keywords in ALLERGEN_INGREDIENTS.items():
            for _, row in df.iterrows():
                ing_has  = ingredients_contain(row.get("base_ingredients",""), keywords)
                all_flag = allergen.lower() in str(row.get("allergens","")).lower()
                if ing_has and not all_flag:
                    allergen_blind[allergen] += 1
    issues["allergen_empty_count"] = allergen_empty
    issues["allergen_blind_spots"] = dict(allergen_blind)

    return dict(issues)


# ══════════════════════════════════════════════════════════════════════════════
# PART C — CLINICAL DISTRIBUTION AUDIT
# ══════════════════════════════════════════════════════════════════════════════

def audit_clinical(df: pd.DataFrame, state: str) -> dict:
    """Check if the dataset has enough safe meals per condition."""
    coverage = {}

    # Diabetes — need Low GI meals per meal type
    diabetes_ok = True
    if "glycemic_index" in df.columns and "meal_type" in df.columns:
        low_gi = df[df["glycemic_index"].str.lower() == "low"]
        for mtype in ["Breakfast", "Lunch", "Snack", "Dinner"]:
            count = len(low_gi[low_gi["meal_type"].str.title() == mtype])
            if count < 14:
                diabetes_ok = False
        coverage["diabetes"] = "Sufficient" if diabetes_ok else "Insufficient"

    # Hypertension — need Low Sodium meals
    hyper_ok = True
    if "sodium_level" in df.columns and "meal_type" in df.columns:
        low_sod = df[df["sodium_level"].str.lower() == "low"]
        for mtype in ["Breakfast", "Lunch", "Snack", "Dinner"]:
            count = len(low_sod[low_sod["meal_type"].str.title() == mtype])
            if count < 14:
                hyper_ok = False
        coverage["hypertension"] = "Sufficient" if hyper_ok else "Insufficient"

    # Weight Loss — need < 450 cal meals
    if "calories" in df.columns:
        count = int((pd.to_numeric(df["calories"], errors="coerce") < 450).sum())
        coverage["weight_loss"] = "Sufficient" if count >= 28 else "Insufficient"

    # Protein variety
    variety_score = 0
    if "base_ingredients" in df.columns:
        protein_sources = ["chicken","fish","mutton","paneer","egg","lentil","dal",
                           "soya","tofu","beans","peas","chana","rajma"]
        combined = " ".join(df["base_ingredients"].fillna("").str.lower())
        variety_score = sum(1 for p in protein_sources if p in combined)
    coverage["protein_variety_score"] = variety_score
    coverage["protein_variety"] = "Good" if variety_score >= 5 else "Low"

    return coverage


# ══════════════════════════════════════════════════════════════════════════════
# PART D — AUTO-CORRECTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def auto_correct(df: pd.DataFrame, state: str, corrections_log: list) -> pd.DataFrame:
    """Auto-fix what is safely fixable. Returns corrected dataframe."""

    # 16 — Standardise text
    df = standardise_text(df)

    # 17 — Fill missing numeric with state-specific median
    num_cols = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]
    for col in num_cols:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        n_missing = df[col].isna().sum()
        if n_missing > 0:
            state_median = df[col].median()
            df[col].fillna(state_median, inplace=True)
            corrections_log.append({
                "state": state, "action": "fill_missing",
                "column": col, "count": int(n_missing),
                "value_used": float(state_median)
            })

    # 18 — Recalculate calories where macro math fails >15%
    macro_cols = ["protein_g", "carbs_g", "fat_g", "calories"]
    if all(c in df.columns for c in macro_cols):
        expected = (df["protein_g"] * 4) + (df["carbs_g"] * 4) + (df["fat_g"] * 9)
        deviation = ((df["calories"] - expected).abs() / expected.replace(0, np.nan)) * 100
        bad_mask  = deviation > 15
        n_fixed   = int(bad_mask.sum())
        if n_fixed > 0:
            df.loc[bad_mask, "calories"] = expected[bad_mask].round(1)
            corrections_log.append({
                "state": state, "action": "recalculate_calories",
                "count": n_fixed
            })

    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN AUDIT RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_full_audit():
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {DATA_DIR.resolve()}")
        return

    print(f"\n{'═'*62}")
    print(f"  INDIE DIETYY — DATASET INTELLIGENCE AUDIT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*62}\n")
    print(f"Found {len(csv_files)} state dataset files.\n")

    all_structural   = []
    all_nutritional  = []
    all_clinical     = []
    corrections_log  = []
    all_dfs          = {}

    all_column_sets  = {}

    # ── PART A ────────────────────────────────────────────────────────────────
    print(f"{'─'*62}")
    print("PART A — STRUCTURAL AUDIT")
    print(f"{'─'*62}")

    for fp in csv_files:
        result = audit_structural(fp)
        state  = result["state"]
        df     = result.pop("df")
        all_dfs[state] = df
        all_structural.append(result)
        all_column_sets[state] = set(result["columns"])

        print(f"\n▶ {state}")
        print(f"  Rows: {result['rows']:,}  |  Columns: {len(result['columns'])}")
        if result["col_changes"]:
            print(f"  Column renames:")
            for ch in result["col_changes"]:
                print(f"    {ch}")
        miss_cols = {c: v for c, v in result["missing"].items() if v > 0}
        if miss_cols:
            print(f"  Missing values: " +
                  ", ".join(f"{c}={v}({result['missing_pct'][c]}%)" for c, v in miss_cols.items()))
        if result["duplicates"] > 0:
            print(f"  ⚠ Duplicate rows: {result['duplicates']}")

    # Column consistency check across all states
    print(f"\n{'─'*62}")
    print("COLUMN CONSISTENCY CHECK (across 28 states)")
    print(f"{'─'*62}")
    all_cols = set()
    for cols in all_column_sets.values():
        all_cols.update(cols)
    for col in sorted(all_cols):
        states_missing = [s for s, cols in all_column_sets.items() if col not in cols]
        if states_missing:
            print(f"  ⚠ '{col}' missing in: {', '.join(states_missing)}")

    # Cross-state row count table
    print(f"\n{'─'*62}")
    print("CROSS-STATE ROW COUNT TABLE")
    print(f"{'─'*62}")
    total_meals = 0
    for r in all_structural:
        print(f"  {r['state']:<30} {r['rows']:>6,} rows")
        total_meals += r["rows"]
    print(f"  {'TOTAL':<30} {total_meals:>6,} meals\n")

    # ── PART B ────────────────────────────────────────────────────────────────
    print(f"{'─'*62}")
    print("PART B — NUTRITIONAL INTEGRITY AUDIT")
    print(f"{'─'*62}\n")

    total_macro_fails = 0
    total_impossible  = 0
    total_gi_issues   = 0
    total_allergen_empty = 0
    total_blind_spots = defaultdict(int)

    for state, df in all_dfs.items():
        issues = audit_nutritional(df, state)
        all_nutritional.append({"state": state, **issues})

        total_macro_fails    += issues.get("macro_math_failures", 0)
        total_impossible     += issues.get("low_calorie_meals", 0) + issues.get("high_calorie_meals", 0)
        total_gi_issues      += issues.get("gi_consistency_issues", 0)
        total_allergen_empty += issues.get("allergen_empty_count", 0)
        for alg, cnt in issues.get("allergen_blind_spots", {}).items():
            total_blind_spots[alg] += cnt

        macro_f = issues.get("macro_math_failures", 0)
        low_c   = issues.get("low_calorie_meals", 0)
        high_c  = issues.get("high_calorie_meals", 0)
        gi_i    = issues.get("gi_consistency_issues", 0)
        flags   = []
        if macro_f > 0:  flags.append(f"macro_fails={macro_f}")
        if low_c > 0:    flags.append(f"low_cal={low_c}")
        if high_c > 0:   flags.append(f"high_cal={high_c}")
        if gi_i > 0:     flags.append(f"gi_issues={gi_i}")
        status = "✅ CLEAN" if not flags else "⚠  " + " | ".join(flags)
        print(f"  {state:<30} {status}")

    # ── PART C ────────────────────────────────────────────────────────────────
    print(f"\n{'─'*62}")
    print("PART C — CLINICAL COVERAGE MATRIX")
    print(f"{'─'*62}")
    print(f"  {'State':<30} {'Diabetes':<14} {'Hypert.':<14} {'Wt Loss':<12} {'Protein Variety'}")
    print(f"  {'-'*28} {'-'*12} {'-'*12} {'-'*10} {'-'*15}")

    clinical_insufficient = 0
    for state, df in all_dfs.items():
        cov = audit_clinical(df, state)
        all_clinical.append({"state": state, **cov})
        d  = cov.get("diabetes",      "N/A")
        h  = cov.get("hypertension",  "N/A")
        wl = cov.get("weight_loss",   "N/A")
        pv = cov.get("protein_variety","N/A")
        if "Insufficient" in (d, h, wl):
            clinical_insufficient += 1
        d_sym  = "✅" if d  == "Sufficient" else "⚠ "
        h_sym  = "✅" if h  == "Sufficient" else "⚠ "
        wl_sym = "✅" if wl == "Sufficient" else "⚠ "
        pv_sym = "✅" if pv == "Good"       else "⚠ "
        print(f"  {state:<30} {d_sym} {d:<12} {h_sym} {h:<12} {wl_sym} {wl:<10} {pv_sym} {pv}")

    # ── HEALTHCARE RISK REPORT ─────────────────────────────────────────────
    macro_pct = round(total_macro_fails / max(total_meals, 1) * 100, 2)
    allergen_ratio = total_allergen_empty / max(total_meals, 1)
    quality = (
        "EXCELLENT" if total_macro_fails < total_meals * 0.01 and allergen_ratio < 0.10 else
        "GOOD"      if total_macro_fails < total_meals * 0.05 and allergen_ratio < 0.30 else
        "FAIR"      if total_macro_fails < total_meals * 0.15 else
        "POOR"
    )

    print(f"\n{'═'*62}")
    print("  INDIE DIETYY — DATA QUALITY RISK REPORT")
    print(f"{'─'*62}")
    print(f"  Total meals audited     │ {total_meals:,}")
    print(f"  Macro math failures     │ {total_macro_fails:,} ({macro_pct}%)")
    print(f"  Impossible calories     │ {total_impossible:,}")
    print(f"  GI consistency issues   │ {total_gi_issues:,}")
    print(f"  Allergen empty rows     │ {total_allergen_empty:,}")
    print(f"  Allergen blind spots    │ {sum(total_blind_spots.values()):,}")
    print(f"  Clinical gaps (states)  │ {clinical_insufficient} states")
    print(f"  Overall data quality    │ {quality}")
    print(f"{'═'*62}\n")

    if quality == "POOR":
        print("🔴 CRITICAL: Data quality is POOR. Fix before training models.\n")

    # ── PART D — AUTO-CORRECTION ───────────────────────────────────────────
    print(f"{'─'*62}")
    print("PART D — AUTO-CORRECTION ENGINE")
    print(f"{'─'*62}")

    cleaned_dfs = []
    for state, df in all_dfs.items():
        df_clean = auto_correct(df.copy(), state, corrections_log)
        cleaned_dfs.append(df_clean)

    master_df = pd.concat(cleaned_dfs, ignore_index=True)

    try:
        import pyarrow
        master_df.to_parquet("data/master_dataset.parquet", index=False)
        print(f"\n  ✅ Saved master_dataset.parquet  ({len(master_df):,} rows)")
    except ImportError:
        master_df.to_csv("data/master_dataset.csv", index=False)
        print(f"\n  ✅ Saved master_dataset.csv  ({len(master_df):,} rows)  [pyarrow not installed]")

    print(f"  ✅ Auto-corrections applied: {len(corrections_log)} operations")

    # ── SAVE REPORTS ──────────────────────────────────────────────────────
    report_json = {
        "generated_at":         datetime.now().isoformat(),
        "total_meals":          total_meals,
        "total_states":         len(csv_files),
        "macro_math_failures":  total_macro_fails,
        "impossible_calories":  total_impossible,
        "gi_issues":            total_gi_issues,
        "allergen_empty":       total_allergen_empty,
        "allergen_blind_spots": dict(total_blind_spots),
        "overall_quality":      quality,
        "structural":           all_structural,
        "nutritional":          all_nutritional,
        "clinical":             all_clinical,
    }

    with open(REPORT_DIR / "dataset_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2, default=str)

    with open(REPORT_DIR / "auto_corrections.json", "w", encoding="utf-8") as f:
        json.dump(corrections_log, f, indent=2)

    # text summary
    txt_lines = [
        "INDIE DIETYY — DATASET AUDIT REPORT",
        f"Generated: {datetime.now().isoformat()}",
        f"Total meals: {total_meals:,}",
        f"Overall quality: {quality}",
        f"Macro math failures: {total_macro_fails} ({macro_pct}%)",
        f"Impossible calories: {total_impossible}",
        f"GI consistency issues: {total_gi_issues}",
        f"Allergen blind spots: {sum(total_blind_spots.values())}",
        f"Clinical gaps: {clinical_insufficient} states",
        "",
        "STATE ROW COUNTS:",
    ]
    for r in all_structural:
        txt_lines.append(f"  {r['state']}: {r['rows']:,}")

    (REPORT_DIR / "dataset_audit_report.txt").write_text(
        "\n".join(txt_lines), encoding="utf-8"
    )

    print(f"\n  ✅ Reports saved to reports/")
    print(f"     - dataset_audit_report.json")
    print(f"     - dataset_audit_report.txt")
    print(f"     - auto_corrections.json")
    print(f"\n{'═'*62}")
    print(f"  AUDIT COMPLETE — Overall Quality: {quality}")
    print(f"{'═'*62}\n")

    return quality


if __name__ == "__main__":
    # Ensure data/ output dir exists
    Path("data").mkdir(exist_ok=True)
    run_full_audit()
