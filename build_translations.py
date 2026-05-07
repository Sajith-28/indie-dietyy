"""
build_translations.py — Indie Dietyy Precomputed Translation Pipeline
Generates 100% precomputed JSON dictionaries for UI and Food Dataset to enable 0ms latency.
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import time
import argparse
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound, TooManyRequests

DATA_DIR = Path("data")
LOCALES_DIR = Path("locales")
FRONTEND_LOCALES_DIR = Path("frontend/public/locales")
LOCALES_DIR.mkdir(exist_ok=True)
FRONTEND_LOCALES_DIR.mkdir(parents=True, exist_ok=True)

# All 10 languages supported by the app
LANGUAGE_CODES = [
    "ta",  # Tamil
    "hi",  # Hindi
    "te",  # Telugu
    "kn",  # Kannada
    "ml",  # Malayalam
    "bn",  # Bengali
    "mr",  # Marathi
    "pa",  # Punjabi
    "or",  # Odia
    "gu",  # Gujarati
    "en"   # English (Default - skipped)
]

# ALL UI strings from the TEXT object in main.js
CORE_UI_STRINGS = [
    # App header & landing
    "Clinical Nutrition OS",
    "Indie Dietyy",
    "Advanced Clinical AI Diet Planner",
    "Personalized Indian diet plans shaped by region, preferences, allergies, BMI, and clinical markers.",
    "Start Clinical Profile",
    "View Last Generated Plan",
    # Wizard navigation
    "Your Profile",
    "Personal Details",
    "Start with the essentials. BMI updates live as your body metrics change.",
    "Name",
    "Enter your name",
    "Age",
    "Weight (kg)",
    "Height (cm)",
    "Calculated BMI",
    # Region & diet step
    "Region & Diet",
    "Tell the planner where your food habits live and what diet style it should respect.",
    "State",
    "Diet Type",
    "Your Goal",
    "Select Preferred Meats (Mandatory)",
    "Choose the proteins you actually want included in the weekly plan.",
    # Clinical step
    "Clinical Conditions (Optional)",
    "Add clinical signals only if relevant. These values are sent to the AI backend for safer recommendations.",
    "Diabetes (Check to add)",
    "Fasting Blood Sugar (mg/dL)",
    "Blood Pressure (Check to add)",
    "Systolic BP (Upper, e.g. 120)",
    "Diastolic BP (Lower, e.g. 80)",
    "High Cholesterol (Check to add)",
    "Total Cholesterol (mg/dL)",
    # Allergies & review
    "Allergies (Free Text)",
    "e.g. Milk, Peanuts, Ghee...",
    "Allergies & Review",
    "One last scan before the backend creates your personalized 7-day plan.",
    # Actions & states
    "Generate 7-Day Plan",
    "AI is generating plan...",
    "Translating UI...",
    "Next",
    "Back",
    "Back to Edit Profile",
    "Download PDF",
    "Fill out your medical profile to generate an intelligent, safe diet plan.",
    # Result page
    "User",
    "AI Score",
    "kcal",
    "Protein",
    "Carbs",
    "Fat",
    "Fiber",
    "Day",
    "Ingredients",
    "BMI",
    "Failed to connect to the AI Backend.",
    "Clinical Disclaimer: This plan is AI-generated. Consult a registered dietitian before following if you have a diagnosed medical condition.",
    # Dropdown labels
    "Vegetarian",
    "Non-Vegetarian",
    "Both",
    "Vegan",
    "Balanced Diet",
    "Weight Loss",
    "Weight Gain",
    # Generating screen status
    "Analyzing BMI",
    "Checking clinical markers",
    "Balancing regional meals",
    "Optimizing macros",
    "Preparing 7-day plan",
    # Plan & state messages
    "Saved Plan",
    "No diet plan yet",
    "Create your profile first and Indie Dietyy will render the generated plan here.",
    "Your clinical diet plan is ready",
    # Meal types (as displayed in results)
    "Breakfast",
    "Lunch",
    "Snack",
    "Dinner",
    # Medical & nutrition terms
    "Calories",
    "Low GI",
    "Low Sodium",
    "Heart Healthy",
    "Welcome to Indie Dietyy",
    "Select your state",
    "Select your language",
    "Calculate my diet plan",
    "Your 7-Day Precision Diet Plan",
    # Landing page (about section)
    "The Engine",
    "Intelligent Clinical Nutrition",
    "Engineered By",
    "Lead AI & Full Stack Developer",
    "Core Developer",
    "Move cursor to explore",
    "Scroll down to explore",
]

def load_all_unique_strings(limit: int = None) -> list:
    """Extracts all unique translatable strings from the dataset, sorted by frequency."""
    dataset_path = DATA_DIR / "processed_dataset.parquet"
    if not dataset_path.exists():
        print("[WARNING] processed_dataset.parquet not found. Skipping food translations.")
        return []
        
    df = pd.read_parquet(dataset_path)
    
    cols_to_translate = ['meal_name', 'base_ingredients', 'instructions', 'exercise_recommendation', 'medical_warning']
    
    print("Extracting unique strings across all columns...")
    string_counts = pd.Series(dtype=int)
    for col in cols_to_translate:
        if col in df.columns:
            counts = df[col].dropna().value_counts()
            string_counts = string_counts.add(counts, fill_value=0)
            
    sorted_strings = string_counts.sort_values(ascending=False).index.tolist()
    
    if limit:
        print(f"Limiting to top {limit} strings for this run...")
        return sorted_strings[:limit]
    return sorted_strings

def safe_translate(text: str, target_lang: str, retries: int = 3) -> str:
    """Translates text with exponential backoff for rate limits."""
    if target_lang == "en" or not text or not str(text).strip():
        return str(text)
        
    for attempt in range(retries):
        try:
            translated = GoogleTranslator(source='en', target=target_lang).translate(str(text))
            return translated if translated else str(text)
        except (TranslationNotFound, TooManyRequests) as e:
            if attempt == retries - 1:
                return str(text)
            time.sleep(2 ** attempt)
        except Exception:
            return str(text)
            
    return str(text)

def translate_batch(strings: list, target_lang: str, cache: dict, max_workers: int = 5):
    """Translate a list of strings concurrently, using existing cache."""
    to_translate = [s for s in strings if s not in cache]
    
    if not to_translate:
        print(f"  [{target_lang}] All {len(strings)} strings already cached. Skipping.")
        return cache
        
    print(f"  [{target_lang}] Translating {len(to_translate)} new strings ({len(strings) - len(to_translate)} cached) using {max_workers} threads...")
    
    processed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(safe_translate, text, target_lang): text for text in to_translate}
        for future in as_completed(futures):
            original_text = futures[future]
            try:
                translated_text = future.result()
                cache[original_text] = translated_text
            except Exception as e:
                cache[original_text] = original_text
                
            processed += 1
            if processed % 50 == 0:
                print(f"  [{target_lang}] Progress: {processed}/{len(to_translate)}")
                
    return cache

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Limit the number of dataset strings to translate (for testing)')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent translation threads')
    parser.add_argument('--ui-only', action='store_true', help='Only translate UI strings, skip food dataset')
    args = parser.parse_args()

    print("\n" + "="*62)
    print("  INDIE DIETYY — PRECOMPUTED TRANSLATION PIPELINE")
    print(f"  Translating {len(CORE_UI_STRINGS)} UI strings across {len(LANGUAGE_CODES)-1} languages")
    print("="*62 + "\n")

    dataset_strings = []
    if not args.ui_only:
        dataset_strings = load_all_unique_strings(limit=args.limit)
        print(f"Total dataset strings to process: {len(dataset_strings)}")

    for lang in LANGUAGE_CODES:
        if lang == "en":
            continue
            
        print(f"\n--- Processing Language: {lang.upper()} ---")
        
        # 1. UI Translations (Save to frontend public dir for 0ms latency UI switch)
        ui_path = FRONTEND_LOCALES_DIR / f"ui_{lang}.json"
        ui_cache = {}
        if ui_path.exists():
            with open(ui_path, "r", encoding="utf-8") as f:
                try:
                    ui_cache = json.load(f)
                except json.JSONDecodeError:
                    ui_cache = {}
                    
        ui_cache = translate_batch(CORE_UI_STRINGS, lang, ui_cache, max_workers=args.workers)
        with open(ui_path, "w", encoding="utf-8") as f:
            json.dump(ui_cache, f, ensure_ascii=False, indent=2)
        print(f"  ✓ UI translations saved → {ui_path} ({len(ui_cache)} entries)")
            
        # 2. Food Dataset Translations (Save to backend locales dir)
        if dataset_strings:
            food_path = LOCALES_DIR / f"food_{lang}.json"
            food_cache = {}
            if food_path.exists():
                with open(food_path, "r", encoding="utf-8") as f:
                    try:
                        food_cache = json.load(f)
                    except json.JSONDecodeError:
                        food_cache = {}
                        
            food_cache = translate_batch(dataset_strings, lang, food_cache, max_workers=args.workers)
            with open(food_path, "w", encoding="utf-8") as f:
                json.dump(food_cache, f, ensure_ascii=False, indent=2)
            print(f"  ✓ Food translations saved → {food_path} ({len(food_cache)} entries)")
            
    print("\n" + "="*62)
    print("  ✅ TRANSLATION PIPELINE COMPLETE.")
    print("  Backend and Frontend JSON dictionaries updated successfully.")
    print("="*62 + "\n")

if __name__ == "__main__":
    main()
