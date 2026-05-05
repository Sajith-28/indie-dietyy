"""
build_translations.py — Indie Dietyy Phase 1 (Language System)
Extracts UI strings and core dataset terms and pre-translates them
into all required Indian languages using deep-translator.
Implements the 3-Layer Translation Approach (JSON caching).
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import time
import pandas as pd
from pathlib import Path
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound, TooManyRequests

DATA_DIR = Path("data")
LOCALES_DIR = Path("locales")
LOCALES_DIR.mkdir(exist_ok=True)

# Required mappings from the prompt
LANGUAGE_CODES = [
    "te", "bn", "as", "hi", "kok", "gu", "kn", "ml", 
    "mr", "mni", "en", "lus", "or", "pa", "ne", "ta"
]

# Core UI Strings for the application frontend
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

def load_dataset_terms() -> list[str]:
    """Extract top 100 unique food names to pre-translate to save runtime latency."""
    dataset_path = DATA_DIR / "processed_dataset.parquet"
    if not dataset_path.exists():
        print("[WARNING] processed_dataset.parquet not found. Skipping food extraction.")
        return []
        
    df = pd.read_parquet(dataset_path)
    # Get top 100 most common meal names to pre-translate
    top_meals = df['meal_name'].value_counts().head(100).index.tolist()
    return top_meals


def safe_translate(text: str, target_lang: str, retries: int = 3) -> str:
    """Translate text with retry logic for rate limits."""
    if target_lang == "en":
        return text
        
    for attempt in range(retries):
        try:
            # GoogleTranslator handles 'kok' (Konkani), 'mni' (Meitei/Manipuri), 'lus' (Mizo) if supported by Google
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            return translated if translated else text
        except (TranslationNotFound, TooManyRequests) as e:
            if attempt == retries - 1:
                return text  # Fallback to English
            time.sleep(1.5) # rate limit backoff
        except Exception as e:
            return text
            
    return text


def build_translation_cache():
    print("\n" + "="*62)
    print("  INDIE DIETYY — PHASE 1: LANGUAGE & TRANSLATION SYSTEM")
    print("="*62 + "\n")

    # Load existing caches if they exist
    ui_cache_path = LOCALES_DIR / "translations.json"
    food_cache_path = LOCALES_DIR / "food_translations.json"
    
    ui_translations = {}
    if ui_cache_path.exists():
        with open(ui_cache_path, "r", encoding="utf-8") as f:
            ui_translations = json.load(f)
            
    food_translations = {}
    if food_cache_path.exists():
        with open(food_cache_path, "r", encoding="utf-8") as f:
            food_translations = json.load(f)

    food_terms = load_dataset_terms()

    print(f"  -> Building translations for {len(LANGUAGE_CODES)} Indian languages...")
    
    for lang in LANGUAGE_CODES:
        if lang not in ui_translations:
            ui_translations[lang] = {}
        if lang not in food_translations:
            food_translations[lang] = {}
            
        print(f"     Translating to '{lang}'...")
        
        # 1. Translate UI Strings (Layer 1)
        for text in CORE_UI_STRINGS:
            if text not in ui_translations[lang]:
                ui_translations[lang][text] = safe_translate(text, lang)
                
        # 2. Translate Top Food Strings (Layer 2)
        for food in food_terms:
            if food not in food_translations[lang]:
                # Delay to respect free API limits
                time.sleep(0.1) 
                food_translations[lang][food] = safe_translate(food, lang)
                
    # Save the JSON caches
    print("\n  -> Saving Layer 1 cache (translations.json)...")
    with open(ui_cache_path, "w", encoding="utf-8") as f:
        json.dump(ui_translations, f, ensure_ascii=False, indent=2)
        
    print("  -> Saving Layer 2 cache (food_translations.json)...")
    with open(food_cache_path, "w", encoding="utf-8") as f:
        json.dump(food_translations, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*62}")
    print("  TRANSLATION CACHES BUILT SUCCESSFULLY.")
    print(f"  Layer 1 (UI): {len(CORE_UI_STRINGS)} keys × {len(LANGUAGE_CODES)} languages")
    print(f"  Layer 2 (Food): {len(food_terms)} keys × {len(LANGUAGE_CODES)} languages")
    print("  Layer 3 (Auto-cache) will handle the rest at runtime.")
    print("="*62 + "\n")


if __name__ == "__main__":
    build_translation_cache()
