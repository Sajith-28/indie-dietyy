"""
feature_engineering.py — Indie Dietyy Phase 2
Prepares the data for clinical AI models.
Computes target labels (health_score, safety_label), applies scaling,
and performs strict geographic state-wise train/test splitting.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from sklearn.preprocessing import StandardScaler, LabelEncoder
from imblearn.over_sampling import SMOTE

DATA_DIR  = Path("data")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

# 2 states held out completely for the final test
HELD_OUT_STATES = ["Kerala", "Punjab"]

def compute_safety_label(row: pd.Series) -> int:
    """
    Computes Random Forest target variable (safety_label).
    0 = Safe, 1 = Caution, 2 = Unsafe
    """
    score = 0
    
    # High sodium -> +1 or +2
    if row.get("sodium_score", 0) == 3: score += 2
    elif row.get("sodium_score", 0) == 2: score += 1
        
    # High GI -> +1 or +2
    if row.get("gi_score", 0) == 3: score += 2
    elif row.get("gi_score", 0) == 2: score += 1
        
    # Extreme macros
    if row.get("calories", 0) > 800: score += 1
    if row.get("fat_g", 0) > 30: score += 1
        
    if score >= 3:
        return 2  # Unsafe
    elif score >= 1:
        return 1  # Caution
    return 0      # Safe


def compute_health_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute target regression scores for the XGBoost/LightGBM models.
    Higher score = healthier/better match.
    """
    print("  -> Computing target safety and health scores...")
    df["safety_label"] = df.apply(compute_safety_label, axis=1)
    
    # Generic health score (0-100)
    # Penalise high GI, high sodium. Reward protein, fiber.
    base_score = 70
    df["meal_health_score"] = (
        base_score 
        - (df["gi_score"] * 5) 
        - (df["sodium_score"] * 5)
        + (df["fiber_g"] * 1.5)
        + (df["protein_g"] * 0.5)
        - (df["fat_g"] * 0.2)
    )
    df["meal_health_score"] = df["meal_health_score"].clip(0, 100)
    
    # Condition-specific targets
    df["diabetes_score"] = df["meal_health_score"] - (df["gi_score"] * 10) + (df["fiber_g"] * 2)
    df["diabetes_score"] = df["diabetes_score"].clip(0, 100)
    
    df["hypertension_score"] = df["meal_health_score"] - (df["sodium_score"] * 15)
    df["hypertension_score"] = df["hypertension_score"].clip(0, 100)
    
    df["weight_loss_score"] = df["meal_health_score"] - (df["calories"] * 0.05) + (df["protein_g"] * 0.5)
    df["weight_loss_score"] = df["weight_loss_score"].clip(0, 100)
    
    df["weight_gain_score"] = df["meal_health_score"] + (df["calories"] * 0.05) + (df["protein_g"] * 0.5)
    df["weight_gain_score"] = df["weight_gain_score"].clip(0, 100)
    
    # New condition: High Cholesterol (rewards low cholesterol_impact)
    df["cholesterol_score"] = df["meal_health_score"] - (df["chol_score"] * 15)
    df["cholesterol_score"] = df["cholesterol_score"].clip(0, 100)
    
    return df


def engineer_and_split():
    print("\n" + "="*62)
    print("  INDIE DIETYY — PHASE 2: FEATURE ENGINEERING")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*62 + "\n")
    
    parquet_path = DATA_DIR / "processed_dataset.parquet"
    if not parquet_path.exists():
        print(f"  [ERROR] {parquet_path} not found. Run merge_data.py first.")
        return
        
    df = pd.read_parquet(parquet_path)
    
    # 1. Compute target labels
    df = compute_health_scores(df)
    
    # 2. Strict Geographic Hold-out Split
    print(f"  -> Applying strict geographic split...")
    print(f"     Held-out states (Test only): {HELD_OUT_STATES}")
    
    test_mask  = df["state"].isin(HELD_OUT_STATES)
    train_mask = ~test_mask
    
    df_train = df[train_mask].copy()
    df_test  = df[test_mask].copy()
    
    print(f"     Train rows: {len(df_train):,} | Test rows: {len(df_test):,}")
    
    # 3. Scaling numeric features
    print("  -> Fitting Standard Scaler on training data...")
    numeric_features = [
        "calories", "protein_g", "carbs_g", "fat_g", "fiber_g",
        "caloric_density", "protein_cal_ratio", "carb_cal_ratio", "fat_cal_ratio",
        "gi_score", "sodium_score", "chol_score"
    ]
    
    scaler = StandardScaler()
    df_train[numeric_features] = scaler.fit_transform(df_train[numeric_features])
    df_test[numeric_features]  = scaler.transform(df_test[numeric_features])
    
    # Save the scaler for production
    joblib.dump(scaler, MODEL_DIR / "preprocessors.pkl")
    print("  ✅ Saved preprocessors.pkl")
    
    # 4. Save ML-Ready Dataframes
    df_train.to_parquet(DATA_DIR / "ml_train.parquet", index=False)
    df_test.to_parquet(DATA_DIR / "ml_test.parquet", index=False)
    print("  ✅ Saved ml_train.parquet and ml_test.parquet")
    
    print(f"\n{'='*62}")
    print("  FEATURE ENGINEERING COMPLETE.")
    print("  Ready for STEP 4: train_models.py")
    print("="*62 + "\n")


if __name__ == "__main__":
    engineer_and_split()
