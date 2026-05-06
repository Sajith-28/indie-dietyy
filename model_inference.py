"""
model_inference.py — Indie Dietyy Phase 2
The Inference Engine.
Loads trained models, takes a user profile, applies safety gates,
scores meals, and sequences a 7-day diet plan translated to the local language.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from deep_translator import GoogleTranslator

# ─────────────────────────────────────────────────────────────────────────────
# 1. SETUP & PATHS
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR   = Path("data")
MODEL_DIR  = Path("models")
LOCALE_DIR = Path("locales")

try:
    import torch
    import torch.nn as nn
    
    # Same LSTM architecture as in train_models.py
    class MealSequencerLSTM(nn.Module):
        def __init__(self, input_dim=15, hidden_dim=128, num_layers=2, num_classes=15):
            super(MealSequencerLSTM, self).__init__()
            self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.3)
            self.fc1 = nn.Linear(hidden_dim, 64)
            self.relu = nn.ReLU()
            self.fc2 = nn.Linear(64, num_classes)
            
        def forward(self, x):
            lstm_out, _ = self.lstm(x)
            last_out = lstm_out[:, -1, :]
            out = self.fc1(last_out)
            out = self.relu(out)
            return self.fc2(out)
            
except ImportError:
    torch = None
    nn = None
    MealSequencerLSTM = None

# ─────────────────────────────────────────────────────────────────────────────
# 2. INFERENCE ENGINE CLASS
# ─────────────────────────────────────────────────────────────────────────────
class DietInferenceEngine:
    def __init__(self, db=None):
        print("Loading AI Models and Datasets into memory...")
        # Datasets
        self.df = pd.read_parquet(DATA_DIR / "processed_dataset.parquet")
        
        # Models
        self.scaler     = joblib.load(MODEL_DIR / "preprocessors.pkl")
        self.rf_safety  = joblib.load(MODEL_DIR / "rf_safety.pkl")
        self.kmeans     = joblib.load(MODEL_DIR / "meal_clusters.pkl")
        
        # Condition Models
        self.lgbm_models = {
            "diabetes":     joblib.load(MODEL_DIR / "lgbm_diabetes.pkl"),
            "hypertension": joblib.load(MODEL_DIR / "lgbm_hypertension.pkl"),
            "weight_loss":  joblib.load(MODEL_DIR / "lgbm_weight_loss.pkl"),
            "weight_gain":  joblib.load(MODEL_DIR / "lgbm_weight_gain.pkl"),
            "cholesterol":  joblib.load(MODEL_DIR / "lgbm_cholesterol.pkl"),
            "balanced":     joblib.load(MODEL_DIR / "lgbm_balanced.pkl")
        }
        
        # Neural Network
        if MealSequencerLSTM is not None and torch is not None:
            try:
                self.lstm = MealSequencerLSTM(input_dim=12) # features used for scaling
                self.lstm.load_state_dict(torch.load(MODEL_DIR / "lstm_sequencer.pt", map_location=torch.device('cpu')))
                self.lstm.eval()
            except Exception as e:
                print(f"[Warning] Could not load LSTM accurately. Will fallback to diverse cluster sampling. {e}")
                self.lstm = None
        else:
            print("[Warning] PyTorch not installed. Will fallback to diverse cluster sampling.")
            self.lstm = None

        # MongoDB db handle (optional — passed in from app.py after startup)
        self.db = db
        # Batch of new translations to save to MongoDB (flushed after each request)
        self._pending_saves: list[dict] = []

        # Load Translation Caches
        try:
            with open(LOCALE_DIR / "translations.json", "r", encoding="utf-8") as f:
                self.ui_translations = json.load(f)
            with open(LOCALE_DIR / "food_translations.json", "r", encoding="utf-8") as f:
                self.food_translations = json.load(f)
        except:
            self.ui_translations = {}
            self.food_translations = {}

        self.numeric_features = [
            "calories", "protein_g", "carbs_g", "fat_g", "fiber_g",
            "caloric_density", "protein_cal_ratio", "carb_cal_ratio", "fat_cal_ratio",
            "gi_score", "sodium_score", "chol_score"
        ]

    def translate(self, text, target_lang):
        """4-Layer Translation: Memory -> File Cache -> MongoDB -> Google API"""
        if target_lang == "en" or not text:
            return text

        # Layer 1: In-memory UI cache
        if target_lang in self.ui_translations and text in self.ui_translations[target_lang]:
            return self.ui_translations[target_lang][text]

        # Layer 2: In-memory food cache
        if target_lang in self.food_translations and text in self.food_translations[target_lang]:
            return self.food_translations[target_lang][text]

        # Layer 3: Google Translate API → save to memory + queue for MongoDB
        try:
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            if translated:
                if target_lang not in self.ui_translations:
                    self.ui_translations[target_lang] = {}
                self.ui_translations[target_lang][text] = translated

                # Queue this new translation to be persisted to MongoDB
                self._pending_saves.append({
                    "food_name_en": text,
                    "lang": target_lang,
                    "value": translated,
                })
                return translated
            return text
        except Exception as e:
            print(f"Translation API Error for '{text}': {e}")
            return text

    async def flush_translation_cache(self, db):
        """Persist any newly translated strings to the MongoDB translations collection."""
        if not self._pending_saves or db is None:
            return

        batch = self._pending_saves.copy()
        self._pending_saves.clear()

        for item in batch:
            lang_key = f"translations.{item['lang']}"
            await db.translations.update_one(
                {"food_name_en": item["food_name_en"]},
                {"$set": {lang_key: {"value": item["value"], "source": "api", "verified": False}}},
                upsert=True,
            )
        print(f"✅ Flushed {len(batch)} new translations to MongoDB.")

    def translate_to_english(self, text: str) -> str:
        """Translates user input (like allergies) from any Indian language to English."""
        if not text or len(text.strip()) == 0:
            return ""
        try:
            return GoogleTranslator(source='auto', target='en').translate(text)
        except:
            return text

    def calculate_bmi(self, weight_kg, height_cm):
        if not weight_kg or not height_cm: return 0
        height_m = height_cm / 100
        return weight_kg / (height_m * height_m)

    def auto_classify_conditions(self, profile):
        """Convert raw health data into medical classifications and determine active AI models."""
        active_conditions = set(profile.get("conditions", []))
        classifications = {}
        
        # Blood Sugar (Fasting)
        bs = profile.get("blood_sugar")
        if bs:
            if bs < 70: classifications["blood_sugar"] = "Low"
            elif bs <= 100: classifications["blood_sugar"] = "Normal"
            elif bs <= 125: classifications["blood_sugar"] = "Prediabetes"
            else: 
                classifications["blood_sugar"] = "Diabetes"
                active_conditions.add("diabetes")
                
        # Blood Pressure
        sys_bp = profile.get("systolic_bp")
        dia_bp = profile.get("diastolic_bp")
        if sys_bp and dia_bp:
            if sys_bp < 90 or dia_bp < 60: classifications["blood_pressure"] = "Low"
            elif sys_bp <= 120 and dia_bp <= 80: classifications["blood_pressure"] = "Normal"
            elif sys_bp <= 129 and dia_bp < 80: classifications["blood_pressure"] = "Elevated"
            else:
                classifications["blood_pressure"] = "Hypertension"
                active_conditions.add("hypertension")
                
        # Cholesterol
        chol = profile.get("cholesterol")
        if chol:
            if chol < 200: classifications["cholesterol"] = "Normal"
            elif chol <= 239: classifications["cholesterol"] = "Borderline High"
            else:
                classifications["cholesterol"] = "High"
                active_conditions.add("cholesterol")
                
        # If no specific disease conditions are active, use goal
        models_to_use = list(active_conditions)
        if not models_to_use:
            goal = profile.get("goal", "balanced")
            if goal in self.lgbm_models:
                models_to_use.append(goal)
            else:
                models_to_use.append("balanced")
                
        return classifications, models_to_use

    def generate_plan(self, user_profile):
        print(f"\n[1] Starting generation for: {user_profile.get('name', 'User')} | State: {user_profile['state']}")
        
        # Calculate BMI
        bmi = self.calculate_bmi(user_profile.get('weight_kg'), user_profile.get('height_cm'))
        print(f"    Calculated BMI: {bmi:.1f}")
        
        # Auto Classification
        classifications, active_models = self.auto_classify_conditions(user_profile)
        print(f"    Classifications: {classifications}")
        print(f"    Active AI Models: {active_models}")
        
        # 1. Filter Database (Hard Rules)
        df_filtered = self.df.copy()
        
        # State Filter (Strict Regionality)
        df_filtered = df_filtered[df_filtered["state"].str.lower() == user_profile["state"].lower()]
        
        # Diet Type Filter & Meat Preferences
        dt = user_profile["diet_type"].lower()
        if dt == "vegetarian":
            df_filtered = df_filtered[df_filtered["diet_type"].str.lower() == "vegetarian"]
        elif dt == "vegan":
            df_filtered = df_filtered[df_filtered["diet_type"].str.lower() == "vegan"]
        elif dt in ["non-vegetarian", "both", "non-veg"]:
            if dt == "non-vegetarian" or dt == "non-veg":
                df_filtered = df_filtered[df_filtered["diet_type"].str.lower().isin(["non-vegetarian", "non-veg"])]
            # If "Both", we keep all diet types, but we MUST strictly filter meats
            
            allowed_meats = [m.lower() for m in user_profile.get("meat_prefs", [])]
            # Drop meals that have a meat_type NOT in allowed_meats
            # Assume meals with empty meat_type are veg/safe
            if allowed_meats:
                def is_meat_allowed(meat_val):
                    if pd.isna(meat_val) or str(meat_val).strip() == "": return True
                    meal_meat = str(meat_val).lower().strip()
                    # Basic mapping check
                    for allowed in allowed_meats:
                        if allowed in meal_meat or meal_meat in allowed: return True
                    return False
                    
                df_filtered = df_filtered[df_filtered["meat_type"].apply(is_meat_allowed)]
            else:
                # If they selected Non-Veg but didn't check any meats, safely fallback to Veg to avoid allergies
                df_filtered = df_filtered[df_filtered["diet_type"].str.lower() == "vegetarian"]
            
        # Allergen Filter (NLP Translated)
        raw_allergies = user_profile.get("allergies", "")
        if raw_allergies.strip():
            english_allergies = self.translate_to_english(raw_allergies)
            allergy_list = [a.strip().lower() for a in english_allergies.split(',')]
            print(f"    Detected Allergies (English): {allergy_list}")
            
            for allergy in allergy_list:
                # Direct boolean columns
                col_name = f"allergen_{allergy}"
                if col_name in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered[col_name] == 0]
                else:
                    # Text search fallback
                    df_filtered = df_filtered[~df_filtered["base_ingredients"].str.lower().str.contains(allergy, na=False)]
                
        if len(df_filtered) < 30:
            return {"error": "Not enough meals match these strict criteria."}
            
        # 2. Apply Safety Gate (Random Forest)
        print(f"[2] Applying Clinical Safety Gate to {len(df_filtered)} meals...")
        X_gate = df_filtered[self.numeric_features].fillna(0)
        
        # Ensure we pass all 15 features the RF was trained on
        gate_features = [
            "calories", "protein_g", "carbs_g", "fat_g", "fiber_g",
            "gi_score", "sodium_score", "chol_score",
            "caloric_density", "protein_cal_ratio", "carb_cal_ratio", "fat_cal_ratio",
            "meal_type_encoded", "diet_type_encoded", "state_encoded"
        ]
        
        # Scale the numeric subset, keep categorical as is
        X_scaled = self.scaler.transform(X_gate)
        
        # Reconstruct the 15 feature array for RF
        X_rf = pd.DataFrame(X_scaled, columns=self.numeric_features, index=df_filtered.index)
        for col in ["meal_type_encoded", "diet_type_encoded", "state_encoded"]:
            if col in df_filtered.columns:
                X_rf[col] = df_filtered[col]
            else:
                X_rf[col] = 0

        # Predict Safety (0=Safe, 1=Caution, 2=Unsafe)
        safety_preds = self.rf_safety.predict(X_rf[gate_features])
        
        # Hard drop Unsafe (2) and Caution (1) meals for clinical compliance
        safe_mask = (safety_preds == 0)
        df_safe = df_filtered[safe_mask].copy()
        print(f"    Blocked {len(df_filtered) - len(df_safe)} unsafe/cautionary meals.")
        
        if len(df_safe) < 28:
            return {"error": "Safety constraints eliminated too many meals. Please relax restrictions."}

        # 3. Score Meals with Multiple LightGBM Specialists
        print(f"[3] Scoring meals using {len(active_models)} specialist models...")
        X_score = X_rf[gate_features].loc[df_safe.index]
        
        combined_scores = np.zeros(len(df_safe))
        valid_models = 0
        
        for condition in active_models:
            if condition in self.lgbm_models:
                specialist_model = self.lgbm_models[condition]
                combined_scores += specialist_model.predict(X_score)
                valid_models += 1
                
        if valid_models > 0:
            df_safe["ai_score"] = combined_scores / valid_models
        else:
            df_safe["ai_score"] = self.lgbm_models["balanced"].predict(X_score)
        
        # 4. Meal Sequencing (7 Days)
        print("[4] Sequencing 7-Day Plan...")
        plan = {}
        used_meals = set()
        
        meal_types = ["Breakfast", "Lunch", "Snack", "Dinner"]
        lang = user_profile.get("language", "en")
        
        for day in range(1, 8):
            day_plan = {}
            for mt in meal_types:
                # Filter by meal type
                subset = df_safe[df_safe["meal_type"].str.lower() == mt.lower()]
                
                # Remove already used meals to ensure variety
                subset = subset[~subset["meal_name"].isin(used_meals)]
                
                if len(subset) == 0:
                    # Fallback to used meals if we run out (rare)
                    subset = df_safe[df_safe["meal_type"].str.lower() == mt.lower()]
                    
                # Pick the highest AI scored meal for this slot
                best_meal = subset.sort_values(by="ai_score", ascending=False).iloc[0]
                used_meals.add(best_meal["meal_name"])
                
                # Translate output
                m_name = self.translate(best_meal["meal_name"], lang)
                
                day_plan[self.translate(mt, lang)] = {
                    "meal_name": m_name,
                    "calories": float(best_meal["calories"]),
                    "protein_g": float(best_meal["protein_g"]),
                    "carbs_g": float(best_meal["carbs_g"]),
                    "fat_g": float(best_meal["fat_g"]),
                    "fiber_g": float(best_meal["fiber_g"]),
                    "ingredients": self.translate(str(best_meal.get("base_ingredients", "")), lang),
                    "ai_score": round(float(best_meal["ai_score"]), 2)
                }
            
            day_label = self.translate("Day", lang)
            plan[f"{day_label} {day}"] = day_plan
            
        print("[5] Plan generated successfully!")
        
        # Assemble Final JSON
        result = {
            "metadata": {
                "user_name": user_profile.get("name", "User"),
                "bmi": round(bmi, 1),
                "medical_classifications": classifications,
                "active_ai_models": active_models,
                "title": self.translate("Your 7-Day Precision Diet Plan", lang),
                "disclaimer": self.translate("Clinical Disclaimer: This plan is AI-generated. Consult a registered dietitian before following if you have a diagnosed medical condition.", lang)
            },
            "diet_plan": plan
        }
        
        return result

# ─────────────────────────────────────────────────────────────────────────────
# 3. CLI DEMONSTRATION
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = DietInferenceEngine()
    
    # Test User 1: Kerala, High Cholesterol, Malayalam, Vegetarian
    test_profile_1 = {
        "name": "Arjun",
        "weight_kg": 85,
        "height_cm": 175,
        "state": "Kerala",
        "diet_type": "Vegetarian",
        "goal": "weight_loss",
        "cholesterol": 245, # High
        "allergies": "പാല്, നിലക്കടല", # Malayalam for Dairy, Peanut
        "language": "ml"
    }
    
    # Test User 2: Punjab, Diabetes, Punjabi, Both (Chicken/Egg)
    test_profile_2 = {
        "name": "Harpreet",
        "weight_kg": 90,
        "height_cm": 180,
        "state": "Punjab",
        "diet_type": "Both",
        "meat_prefs": ["Chicken", "Egg"],
        "goal": "balanced",
        "blood_sugar": 135, # Diabetes
        "systolic_bp": 140, # Hypertension
        "diastolic_bp": 90,
        "allergies": "",
        "language": "pa"
    }
    
    print("\n" + "="*60)
    plan_1 = engine.generate_plan(test_profile_1)
    with open("reports/test_inference_kerala.json", "w", encoding="utf-8") as f:
        json.dump(plan_1, f, indent=2, ensure_ascii=False)
    print("✅ Saved Test User 1 output to reports/test_inference_kerala.json")
    
    print("\n" + "="*60)
    plan_2 = engine.generate_plan(test_profile_2)
    with open("reports/test_inference_punjab.json", "w", encoding="utf-8") as f:
        json.dump(plan_2, f, indent=2, ensure_ascii=False)
    print("✅ Saved Test User 2 output to reports/test_inference_punjab.json")
    print("="*60 + "\n")
