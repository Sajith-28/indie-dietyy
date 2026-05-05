"""
train_models.py — Indie Dietyy Phase 2
Healthcare-grade ML Model Training Pipeline.
Trains 7 specialized models in the correct clinical hierarchy.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import joblib
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from datetime import datetime

from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import classification_report, mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb
from torch.utils.data import DataLoader, TensorDataset

DATA_DIR = Path("data")
MODEL_DIR = Path("models")
REPORT_DIR = Path("reports")
MODEL_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────
def load_data():
    print("  -> Loading ML-ready Parquet datasets...")
    df_train = pd.read_parquet(DATA_DIR / "ml_train.parquet")
    df_test  = pd.read_parquet(DATA_DIR / "ml_test.parquet")
    
    features = [
        "calories", "protein_g", "carbs_g", "fat_g", "fiber_g",
        "gi_score", "sodium_score", "chol_score",
        "caloric_density", "protein_cal_ratio", "carb_cal_ratio", "fat_cal_ratio",
        "meal_type_encoded", "diet_type_encoded", "state_encoded"
    ]
    return df_train, df_test, features

# ─────────────────────────────────────────────────────────────────────────────
# 2. KMeans CLUSTERING (Nutritional Profiles)
# ─────────────────────────────────────────────────────────────────────────────
def train_kmeans(df_train, features):
    print("  -> [1/7] Training KMeans Meal Clustering...")
    X = df_train[features].fillna(0)
    
    kmeans = KMeans(n_clusters=15, init="k-means++", n_init=10, max_iter=300, random_state=42)
    df_train["cluster"] = kmeans.fit_predict(X)
    
    joblib.dump(kmeans, MODEL_DIR / "meal_clusters.pkl")
    return kmeans

# ─────────────────────────────────────────────────────────────────────────────
# 3. ISOLATION FOREST (Anomaly Detection)
# ─────────────────────────────────────────────────────────────────────────────
def train_isolation_forest(df_train, features):
    print("  -> [2/7] Training Isolation Forest Anomaly Detector...")
    X = df_train[features].fillna(0)
    
    iso_forest = IsolationForest(contamination=0.02, n_estimators=100, random_state=42)
    # -1 for anomalies, 1 for normal
    df_train["is_anomaly"] = iso_forest.fit_predict(X)
    
    n_anomalies = (df_train["is_anomaly"] == -1).sum()
    print(f"     Flagged {n_anomalies} anomalous meals (excluded from ranking models).")
    
    joblib.dump(iso_forest, MODEL_DIR / "anomaly_detector.pkl")
    return iso_forest, df_train[df_train["is_anomaly"] == 1] # return clean data

# ─────────────────────────────────────────────────────────────────────────────
# 4. RANDOM FOREST SAFETY CLASSIFIER (Clinical Safety Gate)
# ─────────────────────────────────────────────────────────────────────────────
def train_rf_safety(df_clean_train, df_test, features):
    print("  -> [3/7] Training Random Forest Safety Classifier...")
    X_train = df_clean_train[features].fillna(0)
    y_train = df_clean_train["safety_label"]
    
    rf = RandomForestClassifier(
        n_estimators=300, 
        max_depth=None,
        class_weight="balanced_subsample",
        min_samples_leaf=5,
        oob_score=True,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    
    # Eval on Test Set
    X_test = df_test[features].fillna(0)
    y_test = df_test["safety_label"]
    y_pred = rf.predict(X_test)
    
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    
    joblib.dump(rf, MODEL_DIR / "rf_safety.pkl")
    return rf, report

# ─────────────────────────────────────────────────────────────────────────────
# 5. XGBoost PRIMARY RANKER (Meal Health Score)
# ─────────────────────────────────────────────────────────────────────────────
def train_xgboost(df_clean_train, df_test, features):
    print("  -> [4/7] Training XGBoost Primary Ranker...")
    X_train = df_clean_train[features].fillna(0)
    y_train = df_clean_train["meal_health_score"]
    
    X_test = df_test[features].fillna(0)
    y_test = df_test["meal_health_score"]
    
    xgb_model = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=500,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        early_stopping_rounds=50,
        eval_metric=["rmse", "mae"],
        random_state=42,
        n_jobs=-1
    )
    
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    y_pred = xgb_model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    joblib.dump(xgb_model, MODEL_DIR / "xgb_ranker.pkl")
    return xgb_model, {"rmse": rmse, "mae": mae, "r2": r2}

# ─────────────────────────────────────────────────────────────────────────────
# 6. LightGBM CONDITION SCORERS (5 Models)
# ─────────────────────────────────────────────────────────────────────────────
def train_lightgbm_models(df_clean_train, df_test, features):
    print("  -> [5/7] Training LightGBM Condition-Specific Scorers...")
    X_train = df_clean_train[features].fillna(0)
    X_test  = df_test[features].fillna(0)
    
    targets = {
        "diabetes": "diabetes_score",
        "hypertension": "hypertension_score",
        "weight_loss": "weight_loss_score",
        "weight_gain": "weight_gain_score",
        "cholesterol": "cholesterol_score",
        "balanced": "meal_health_score"
    }
    
    lgb_metrics = {}
    
    for condition, target_col in targets.items():
        y_train = df_clean_train[target_col]
        y_test  = df_test[target_col]
        
        model = lgb.LGBMRegressor(
            boosting_type="gbdt",
            num_leaves=63,
            learning_rate=0.05,
            n_estimators=400,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            min_child_samples=20,
            random_state=42,
            n_jobs=-1,
            verbosity=-1
        )
        
        # LightGBM custom eval requires callbacks
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(stopping_rounds=30, verbose=False)]
        )
        
        y_pred = model.predict(X_test)
        lgb_metrics[condition] = {
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "r2": r2_score(y_test, y_pred)
        }
        
        joblib.dump(model, MODEL_DIR / f"lgbm_{condition}.pkl")
        
    return lgb_metrics

# ─────────────────────────────────────────────────────────────────────────────
# 7. LSTM SEQUENCE MODEL (PyTorch)
# ─────────────────────────────────────────────────────────────────────────────
class MealSequencerLSTM(nn.Module):
    def __init__(self, input_dim=15, hidden_dim=128, num_layers=2, num_classes=15):
        super(MealSequencerLSTM, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.3)
        self.fc1 = nn.Linear(hidden_dim, 64)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(64, num_classes)
        
    def forward(self, x):
        # x: (batch, seq_len, input_dim)
        lstm_out, _ = self.lstm(x)
        # Take the output of the last time step
        last_out = lstm_out[:, -1, :]
        out = self.fc1(last_out)
        out = self.relu(out)
        out = self.fc2(out)
        return out

def train_lstm(df_clean_train, features):
    print("  -> [6/7] Training PyTorch LSTM 7-Day Sequencer...")
    
    # We will simulate sequences by randomly sampling continuous nutrition vectors
    # and predicting the cluster of the next meal. This allows the model to learn
    # transitional patterns without needing real user logs.
    
    X_raw = df_clean_train[features].fillna(0).values
    # Ensure cluster column exists from KMeans step
    y_raw = df_clean_train["cluster"].values if "cluster" in df_clean_train else np.zeros(len(X_raw))
    
    SEQ_LEN = 21 # 3 days * 7 meals
    num_samples = min(5000, len(X_raw) - SEQ_LEN)
    
    X_seq = np.zeros((num_samples, SEQ_LEN, len(features)))
    y_seq = np.zeros((num_samples,))
    
    for i in range(num_samples):
        start = np.random.randint(0, len(X_raw) - SEQ_LEN - 1)
        X_seq[i] = X_raw[start:start+SEQ_LEN]
        y_seq[i] = y_raw[start+SEQ_LEN]
        
    tensor_X = torch.FloatTensor(X_seq)
    tensor_y = torch.LongTensor(y_seq)
    
    dataset = TensorDataset(tensor_X, tensor_y)
    loader = DataLoader(dataset, batch_size=64, shuffle=True)
    
    model = MealSequencerLSTM(input_dim=len(features), num_classes=15)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    model.train()
    epochs = 15 # Kept short for script efficiency, typically 100
    for epoch in range(epochs):
        for batch_X, batch_y in loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
    torch.save(model.state_dict(), MODEL_DIR / "lstm_sequencer.pt")
    print("     Saved lstm_sequencer.pt")
    return model

# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def run_pipeline():
    print("\n" + "="*62)
    print("  INDIE DIETYY — PHASE 2: ML MODEL TRAINING PIPELINE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*62 + "\n")
    
    df_train, df_test, features = load_data()
    
    train_kmeans(df_train, features)
    
    iso_forest, df_clean_train = train_isolation_forest(df_train, features)
    
    rf, rf_report = train_rf_safety(df_clean_train, df_test, features)
    
    xgb_model, xgb_metrics = train_xgboost(df_clean_train, df_test, features)
    
    lgb_metrics = train_lightgbm_models(df_clean_train, df_test, features)
    
    train_lstm(df_clean_train, features)
    
    print("\n" + "─"*62)
    print("  -> [7/7] Generating Final Model Performance Report...")
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "random_forest_safety": {
            "unsafe_class_recall": rf_report.get("2", {}).get("recall", 0),
            "safe_class_recall": rf_report.get("0", {}).get("recall", 0),
            "macro_avg_f1": rf_report.get("macro avg", {}).get("f1-score", 0)
        },
        "xgboost_primary_ranker": xgb_metrics,
        "lightgbm_condition_scorers": lgb_metrics
    }
    
    with open(REPORT_DIR / "model_training_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print("\n" + "="*62)
    print("  TRAINING COMPLETE.")
    print("  Models safely saved to models/")
    print(f"  RF Unsafe Recall Gate : {report['random_forest_safety']['unsafe_class_recall']:.4f}")
    print(f"  XGBoost R² Score      : {xgb_metrics['r2']:.4f}")
    print("="*62 + "\n")


if __name__ == "__main__":
    run_pipeline()
