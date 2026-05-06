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

# 9 Primary Languages from Prompt
LANGUAGE_CODES = [
    "ta", # Tamil
    "hi", # Hindi
    "te", # Telugu
    "kn", # Kannada
    "ml", # Malayalam
    "bn", # Bengali
    "mr", # Marathi
    "pa", # Punjabi
    "en"  # English (Default)
]

CORE_UI_STRINGS = [
    "Welcome to Indie Dietyy",
    "Select your state",
    "Select your language",
    "Calculate my diet plan",
    "Your 7-Day Precision Diet Plan",
    "Breakfast", "Lunch", "Snack", "Dinner",
    "Calories", "Protein", "Carbs", "Fat", "Fiber",
    "Vegetarian", "Non-Vegetarian", "Vegan",
    "Low GI", "Low Sodium", "Heart Healthy",
    "Clinical Disclaimer: This plan is AI-generated. Consult a registered dietitian before following if you have a diagnosed medical condition."
]

def load_all_unique_strings(limit: int = None) -> list:
    """Extracts all unique translatable strings from the dataset, sorted by frequency."""
    dataset_path = DATA_DIR / "processed_dataset.parquet"
    if not dataset_path.exists():
        print("[WARNING] processed_dataset.parquet not found.")
        return []
        
    df = pd.read_parquet(dataset_path)
    
    # We want to translate these columns
    cols_to_translate = ['meal_name', 'base_ingredients', 'instructions', 'exercise_recommendation', 'medical_warning']
    
    print("Extracting unique strings across all columns...")
    string_counts = pd.Series(dtype=int)
    for col in cols_to_translate:
        if col in df.columns:
            counts = df[col].dropna().value_counts()
            string_counts = string_counts.add(counts, fill_value=0)
            
    # Sort by most frequent first to prioritize common terms
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
            time.sleep(2 ** attempt) # Exponential backoff: 1s, 2s, 4s
        except Exception:
            return str(text)
            
    return str(text)

def translate_batch(strings: list, target_lang: str, cache: dict, max_workers: int = 5):
    """Translate a list of strings concurrently, using existing cache."""
    to_translate = [s for s in strings if s not in cache]
    
    if not to_translate:
        return cache
        
    print(f"[{target_lang}] Translating {len(to_translate)} new strings using {max_workers} threads...")
    
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
            if processed % 100 == 0:
                print(f"[{target_lang}] Progress: {processed}/{len(to_translate)}")
                
    return cache

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, help='Limit the number of dataset strings to translate (for testing)')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent translation threads')
    args = parser.parse_args()

    print("\n" + "="*62)
    print("  INDIE DIETYY — PRECOMPUTED TRANSLATION PIPELINE")
    print("="*62 + "\n")

    dataset_strings = load_all_unique_strings(limit=args.limit)
    print(f"Total dataset strings to process: {len(dataset_strings)}")

    for lang in LANGUAGE_CODES:
        if lang == "en":
            continue
            
        print(f"\n--- Processing Language: {lang} ---")
        
        # 1. UI Translations (Save to frontend public dir for 0ms latency UI switch)
        ui_path = FRONTEND_LOCALES_DIR / f"ui_{lang}.json"
        ui_cache = {}
        if ui_path.exists():
            with open(ui_path, "r", encoding="utf-8") as f:
                ui_cache = json.load(f)
                
        ui_cache = translate_batch(CORE_UI_STRINGS, lang, ui_cache, max_workers=args.workers)
        with open(ui_path, "w", encoding="utf-8") as f:
            json.dump(ui_cache, f, ensure_ascii=False, indent=2)
            
        # 2. Food Dataset Translations (Save to backend locales dir)
        food_path = LOCALES_DIR / f"food_{lang}.json"
        food_cache = {}
        if food_path.exists():
            with open(food_path, "r", encoding="utf-8") as f:
                food_cache = json.load(f)
                
        food_cache = translate_batch(dataset_strings, lang, food_cache, max_workers=args.workers)
        with open(food_path, "w", encoding="utf-8") as f:
            json.dump(food_cache, f, ensure_ascii=False, indent=2)
            
    print("\n" + "="*62)
    print("  TRANSLATION PIPELINE COMPLETE.")
    print("  Backend and Frontend JSON dictionaries updated successfully.")
    print("="*62 + "\n")

if __name__ == "__main__":
    main()
