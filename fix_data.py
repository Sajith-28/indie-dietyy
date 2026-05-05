"""
fix_data.py — Indie Dietyy Data Quality Fixer
Upgrades dataset quality from POOR → EXCELLENT by:
  1. Recalculating calories from macros (fixes 27% macro failures)
  2. Auto-populating allergen column from base_ingredients
  3. Fixing impossible calorie values
  4. Standardising all text casing
  5. Saving cleaned CSVs back in-place
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_DIR   = Path("datasets")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

# ── Allergen keyword map ──────────────────────────────────────────────────────
ALLERGEN_MAP = {
    "Peanut":   ["peanut", "groundnut", "mungfali"],
    "Dairy":    ["milk", "paneer", "curd", "yogurt", "ghee", "cheese", "butter",
                 "cream", "lassi", "dahi", "khoya", "mawa", "rabri"],
    "Gluten":   ["wheat", "maida", "atta", "bread", "roti", "chapati", "semolina",
                 "suji", "sooji", "naan", "puri", "paratha", "biscuit"],
    "Egg":      ["egg", "anda", "omelette"],
    "Fish":     ["fish", "tuna", "salmon", "mackerel", "sardine", "hilsa", "rohu",
                 "catla", "pomfret", "prawn", "shrimp", "crab", "lobster",
                 "seafood", "meen", "machli"],
    "Nut":      ["almond", "cashew", "walnut", "pistachio", "hazelnut", "badam",
                 "kaju", "akhrot", "pista", "pine nut"],
    "Soy":      ["soy", "tofu", "soybean", "soya"],
    "Mustard":  ["mustard", "sarson"],
    "Sesame":   ["sesame", "til", "gingelly"],
    "Shellfish":["prawn", "shrimp", "crab", "lobster", "mussel", "clam", "oyster"],
}

COLUMN_MAP = {
    "meal name":               "meal_name",
    "dish":                    "meal_name",
    "meal type":               "meal_type",
    "diet type":               "diet_type",
    "meat type":               "meat_type",
    "calories":                "calories",
    "protein (g)":             "protein_g",
    "protein(g)":              "protein_g",
    "protein_g":               "protein_g",
    "carbs (g)":               "carbs_g",
    "carbs(g)":                "carbs_g",
    "carbs_g":                 "carbs_g",
    "fat (g)":                 "fat_g",
    "fat(g)":                  "fat_g",
    "fat_g":                   "fat_g",
    "fiber (g)":               "fiber_g",
    "fiber(g)":                "fiber_g",
    "fiber_g":                 "fiber_g",
    "glycemic index":          "glycemic_index",
    "glycemic_index":          "glycemic_index",
    "sodium level":            "sodium_level",
    "sodium_level":            "sodium_level",
    "cholesterol impact":      "cholesterol_impact",
    "cholesterol_impact":      "cholesterol_impact",
    "allergens":               "allergens",
    "base ingredients":        "base_ingredients",
    "base_ingredients":        "base_ingredients",
    "instructions":            "instructions",
    "exercise recommendation": "exercise_recommendation",
    "exercise":                "exercise_recommendation",
    "medical warning":         "medical_warning",
    "warning":                 "medical_warning",
}


def extract_state_name(filepath: Path) -> str:
    name = filepath.stem
    name = re.sub(r"[\(\d\)]+", "", name)
    name = re.sub(r"_diet_dataset.*$", "", name)
    return name.strip("_ ").replace("_", " ").title()


def load_csv(filepath: Path) -> pd.DataFrame:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(filepath, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {filepath.name}")


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names to canonical form."""
    rename = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in COLUMN_MAP:
            rename[col] = COLUMN_MAP[key]
    df.rename(columns=rename, inplace=True)
    return df


def fix_text_casing(df: pd.DataFrame) -> pd.DataFrame:
    """Title-case all categorical columns."""
    cat_cols = ["meal_type", "diet_type", "glycemic_index",
                "sodium_level", "cholesterol_impact"]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
            df[col] = df[col].replace({"Nan": np.nan, "None": np.nan})
    return df


def fix_macro_calories(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Recalculate Calories where macro-math deviation > 15%.
    Formula: Calories = (Protein*4) + (Carbs*4) + (Fat*9)
    Returns (fixed_df, count_fixed)
    """
    needed = ["calories", "protein_g", "carbs_g", "fat_g"]
    if not all(c in df.columns for c in needed):
        return df, 0

    for col in needed:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    expected  = (df["protein_g"] * 4) + (df["carbs_g"] * 4) + (df["fat_g"] * 9)
    actual    = df["calories"]
    safe_exp  = expected.replace(0, np.nan)
    deviation = ((actual - safe_exp).abs() / safe_exp * 100)

    bad_mask = deviation > 15
    n_fixed  = int(bad_mask.sum())

    if n_fixed > 0:
        df.loc[bad_mask, "calories"] = expected[bad_mask].round(1)

    # Also clamp impossible values (< 30 or > 1200) using state median
    state_median = df.loc[~bad_mask, "calories"].median()
    impossible   = (df["calories"] < 30) | (df["calories"] > 1200)
    n_fixed     += int(impossible.sum())
    df.loc[impossible, "calories"] = state_median

    return df, n_fixed


def detect_allergens_from_ingredients(ingredients_str: str) -> str:
    """
    Scan base ingredients text and return a comma-separated allergen string.
    E.g. "wheat flour, milk, peanut oil" → "Gluten, Dairy, Peanut"
    """
    if pd.isna(ingredients_str) or str(ingredients_str).strip() == "":
        return ""
    text     = str(ingredients_str).lower()
    detected = []
    for allergen, keywords in ALLERGEN_MAP.items():
        if any(kw in text for kw in keywords):
            detected.append(allergen)
    return ", ".join(detected)


def fix_gi_consistency(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Fix GI consistency:
    - If Low but contains rice/sugar -> High
    - If High but contains high fiber veg -> Low
    """
    if not all(c in df.columns for c in ["glycemic_index", "base_ingredients"]):
        return df, 0
    
    RICE_SUGAR_KEYWORDS = ["rice", "sugar", "jaggery", "sweet", "dessert", "kheer", "halwa", "ladoo"]
    HIGH_FIBER_VEGETABLES = ["spinach", "methi", "kale", "broccoli", "cabbage", "beans", "lentil", "dal"]
    
    n_fixed = 0
    df["glycemic_index"] = df["glycemic_index"].astype(str).replace({"nan": np.nan, "None": np.nan})
    df["base_ingredients"] = df["base_ingredients"].fillna("").astype(str)
    
    for idx, row in df.iterrows():
        gi = str(row.get("glycemic_index")).strip().title()
        ing = row.get("base_ingredients").lower()
        
        if gi == "Low" and any(k in ing for k in RICE_SUGAR_KEYWORDS):
            df.at[idx, "glycemic_index"] = "High"
            n_fixed += 1
        elif gi == "High" and any(k in ing for k in HIGH_FIBER_VEGETABLES):
            df.at[idx, "glycemic_index"] = "Low"
            n_fixed += 1
            
    return df, n_fixed

def fix_allergens(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Fill empty allergen fields from base_ingredients scan.
    Also fix blind spots where ingredients contain allergen but column is empty/wrong.
    Returns (fixed_df, count_fixed)
    """
    if "base_ingredients" not in df.columns:
        return df, 0
    if "allergens" not in df.columns:
        df["allergens"] = ""

    df["allergens"] = df["allergens"].astype(str).replace({"nan": "", "None": ""})

    n_fixed = 0

    for idx, row in df.iterrows():
        detected = detect_allergens_from_ingredients(row.get("base_ingredients", ""))
        current  = str(row.get("allergens", "")).strip()

        if not detected:
            # no allergens detected — explicitly set to "Safe" (pandas might nullify "None")
            if current in ("", "nan", "None"):
                df.at[idx, "allergens"] = "Safe"
                n_fixed += 1
            continue

        # Merge detected with existing (avoid duplicates)
        existing_set  = {a.strip() for a in current.split(",") if a.strip() not in ("", "nan", "None")}
        detected_set  = {a.strip() for a in detected.split(",") if a.strip()}
        merged        = existing_set | detected_set

        new_val = ", ".join(sorted(merged))
        if new_val != current:
            df.at[idx, "allergens"] = new_val
            n_fixed += 1

    return df, n_fixed


def fill_missing_numerics(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Fill missing numeric values with state-specific median."""
    num_cols = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]
    n_fixed  = 0
    for col in num_cols:
        if col not in df.columns:
            continue
        df[col]   = pd.to_numeric(df[col], errors="coerce")
        n_missing = int(df[col].isna().sum())
        if n_missing > 0:
            median = df[col].median()
            df[col].fillna(median, inplace=True)
            n_fixed += n_missing
    return df, n_fixed


def fix_fiber(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Cap absurd fiber values (>30g) at the 95th percentile for the state."""
    if "fiber_g" not in df.columns:
        return df, 0
    df["fiber_g"] = pd.to_numeric(df["fiber_g"], errors="coerce")
    cap    = df["fiber_g"].quantile(0.95)
    mask   = df["fiber_g"] > 30
    n      = int(mask.sum())
    df.loc[mask, "fiber_g"] = cap
    return df, n


def fix_protein(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Cap absurd protein values (>60g) at 95th percentile."""
    if "protein_g" not in df.columns:
        return df, 0
    df["protein_g"] = pd.to_numeric(df["protein_g"], errors="coerce")
    cap  = df["protein_g"].quantile(0.95)
    mask = df["protein_g"] > 60
    n    = int(mask.sum())
    df.loc[mask, "protein_g"] = cap
    # Recalculate calories after capping protein
    if all(c in df.columns for c in ["protein_g", "carbs_g", "fat_g"]):
        df.loc[mask, "calories"] = (
            df.loc[mask, "protein_g"] * 4 +
            df.loc[mask, "carbs_g"]   * 4 +
            df.loc[mask, "fat_g"]     * 9
        ).round(1)
    return df, n


# ══════════════════════════════════════════════════════════════════════════════
# MAIN FIX RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_fix():
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {DATA_DIR.resolve()}")
        return

    print("\n" + "="*62)
    print("  INDIE DIETYY — DATA QUALITY FIXER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*62 + "\n")

    total_macro_fixed    = 0
    total_allergen_fixed = 0
    total_numeric_fixed  = 0
    total_fiber_fixed    = 0
    total_protein_fixed  = 0
    fix_log              = []

    for fp in csv_files:
        state = extract_state_name(fp)
        df    = load_csv(fp)
        df    = normalise_columns(df)
        df    = fix_text_casing(df)

        df, nf = fill_missing_numerics(df)
        total_numeric_fixed += nf

        df, mf = fix_macro_calories(df)
        total_macro_fixed += mf

        df, ff = fix_fiber(df)
        total_fiber_fixed += ff

        df, pf = fix_protein(df)
        total_protein_fixed += pf
        
        df, gf = fix_gi_consistency(df)

        df, af = fix_allergens(df)
        total_allergen_fixed += af

        # Save back in-place
        df.to_csv(fp, index=False, encoding="utf-8")

        state_total = mf + af + nf + ff + pf
        flag        = "✅" if state_total == 0 else f"🔧 {state_total} fixes"
        print(f"  {state:<30}  {flag}")

        fix_log.append({
            "state":            state,
            "macro_fixed":      mf,
            "allergen_fixed":   af,
            "numeric_fixed":    nf,
            "fiber_fixed":      ff,
            "protein_fixed":    pf,
        })

    grand_total = (total_macro_fixed + total_allergen_fixed +
                   total_numeric_fixed + total_fiber_fixed + total_protein_fixed)

    print(f"\n{'='*62}")
    print("  FIX SUMMARY")
    print(f"{'─'*62}")
    print(f"  Macro/calorie corrections  : {total_macro_fixed:,}")
    print(f"  Allergen field fixes       : {total_allergen_fixed:,}")
    print(f"  Missing numeric fills      : {total_numeric_fixed:,}")
    print(f"  Fiber cap fixes            : {total_fiber_fixed:,}")
    print(f"  Protein cap fixes          : {total_protein_fixed:,}")
    print(f"{'─'*62}")
    print(f"  TOTAL CORRECTIONS          : {grand_total:,}")
    print(f"{'='*62}\n")

    # Save fix log
    with open(REPORT_DIR / "fix_log.json", "w", encoding="utf-8") as f:
        json.dump({
            "fixed_at":             datetime.now().isoformat(),
            "total_corrections":    grand_total,
            "macro_fixed":          total_macro_fixed,
            "allergen_fixed":       total_allergen_fixed,
            "numeric_fixed":        total_numeric_fixed,
            "state_details":        fix_log,
        }, f, indent=2)

    print("  fix_log.json saved to reports/")
    print("\n  Now re-running dataset_audit.py to verify quality...\n")


if __name__ == "__main__":
    run_fix()

    # Auto re-run the audit to show the new quality score
    import importlib.util, os
    audit_path = Path("dataset_audit.py")
    if audit_path.exists():
        spec   = importlib.util.spec_from_file_location("dataset_audit", audit_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.run_full_audit()
