"""
merge_data.py — Indie Dietyy Phase 1 (Data Prep)
Consolidates the cleaned 28 state CSV files into one master Parquet dataset.
Performs final formatting, one-hot encoding, and feature extraction 
needed by the healthcare AI models in Phase 2.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("datasets")
OUT_DIR  = Path("data")
OUT_DIR.mkdir(exist_ok=True)

def load_and_merge() -> pd.DataFrame:
    """Load all state datasets and merge into one."""
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSVs found in {DATA_DIR.resolve()}")
    
    dfs = []
    for fp in csv_files:
        df = pd.read_csv(fp)
        dfs.append(df)
        
    master_df = pd.concat(dfs, ignore_index=True)
    return master_df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create essential nutritional features and encodings for ML."""
    print("  -> Creating macro density features...")
    
    # 1. Macro ratios (Clinical features)
    df["caloric_density"] = df["calories"] / (df["protein_g"] + df["carbs_g"] + df["fat_g"] + 0.1)
    df["protein_cal_ratio"] = (df["protein_g"] * 4) / (df["calories"] + 0.1)
    df["carb_cal_ratio"]    = (df["carbs_g"] * 4) / (df["calories"] + 0.1)
    df["fat_cal_ratio"]     = (df["fat_g"] * 9)   / (df["calories"] + 0.1)
    
    # 2. Ordinal Encodings for clinical labels
    print("  -> Encoding clinical labels (GI, Sodium, Cholesterol)...")
    gi_map = {"Low": 1, "Medium": 2, "High": 3}
    sod_map = {"Low": 1, "Medium": 2, "High": 3}
    chol_map = {"Low": 1, "Medium": 2, "High": 3}
    
    df["gi_score"] = df["glycemic_index"].map(gi_map).fillna(2.0)
    df["sodium_score"] = df["sodium_level"].map(sod_map).fillna(2.0)
    df["chol_score"] = df["cholesterol_impact"].map(chol_map).fillna(2.0)
    
    # 3. Categorical encodings (State, Diet, Meal Type)
    print("  -> Encoding categorical variables...")
    df["state_encoded"] = df["state"].astype("category").cat.codes
    df["meal_type_encoded"] = df["meal_type"].astype("category").cat.codes
    df["diet_type_encoded"] = df["diet_type"].astype("category").cat.codes
    
    # 4. Allergen Vectorization (for strict filtering)
    print("  -> Vectorizing allergens...")
    allergens_list = ["Peanut", "Dairy", "Gluten", "Egg", "Fish", "Nut", "Soy", "Mustard", "Sesame", "Shellfish"]
    
    for alg in allergens_list:
        df[f"allergen_{alg.lower()}"] = df["allergens"].str.contains(alg, case=False, na=False).astype(int)
        
    return df


def save_dataset(df: pd.DataFrame):
    """Save the final consolidated dataset."""
    print(f"\n  -> Saving master dataset ({len(df):,} rows)...")
    
    # Drop rows that somehow lost critical meal names
    df = df.dropna(subset=["meal_name", "calories"])
    
    # Sort for consistency
    if "state" in df.columns and "meal_name" in df.columns:
        df = df.sort_values(["state", "meal_name"])
        
    # Save as Parquet for high-performance reading in PyTorch/LightGBM
    try:
        parquet_path = OUT_DIR / "processed_dataset.parquet"
        df.to_parquet(parquet_path, index=False)
        print(f"  ✅ Saved Parquet: {parquet_path}")
    except ImportError:
        csv_path = OUT_DIR / "processed_dataset.csv"
        df.to_csv(csv_path, index=False)
        print(f"  ✅ Saved CSV: {csv_path} (Install pyarrow for faster Parquet storage)")

    # Save a lightweight version for the FastAPI backend (dropping heavy text columns)
    lite_cols = [c for c in df.columns if c not in ["instructions", "exercise_recommendation", "medical_warning"]]
    lite_path = OUT_DIR / "backend_dataset.parquet"
    try:
        df[lite_cols].to_parquet(lite_path, index=False)
        print(f"  ✅ Saved Lite Backend Dataset: {lite_path}")
    except:
        pass


def run():
    print("\n" + "="*62)
    print("  INDIE DIETYY — PHASE 1: DATASET MERGE & PREP")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*62 + "\n")
    
    master_df = load_and_merge()
    print(f"  ✅ Loaded 28 CSVs. Total initial rows: {len(master_df):,}")
    
    master_df = engineer_features(master_df)
    save_dataset(master_df)
    
    print(f"\n{'='*62}")
    print("  MERGE COMPLETE.")
    print("  Dataset is ready for Phase 2: Feature Engineering & Model Training.")
    print("="*62 + "\n")

if __name__ == "__main__":
    run()
