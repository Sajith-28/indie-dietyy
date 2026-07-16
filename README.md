# Indie Dietyy

Indie Dietyy is an Indian-region aware, clinically-informed AI diet planner that generates personalized 7-day meal plans. It combines lightweight machine learning models with a neural sequence model to produce culturally relevant menus that respect user preferences, clinical markers (diabetes, blood pressure, cholesterol), allergies, and nutritional goals.

This repository contains:

- `app.py` — FastAPI backend and inference entrypoints.
- `frontend/` — Vite-based single file vanilla JS frontend (`frontend/src/main.js`).
- `models/` — Serialized models and supporting artifacts used by the inference engine.
- `datasets/` — Regional diet datasets used during model development and evaluation (one CSV per Indian state/region).
- `database.py` — MongoDB connection helper (reads `MONGODB_URI` from env).

Goals
-----

- Generate clinically-safe, regionally-appropriate 7-day diet plans.
- Respect diet type (Vegetarian/Non-Vegetarian/Both/Vegan), meat preferences, and allergies.
- Optimize macronutrients and caloric targets for weight loss, gain, or balanced goals.
- Provide explainable outputs (macros, ingredients) and keep a small audit trail in MongoDB when available.

Models and Artifacts
--------------------

The `models/` directory includes several types of models that together form the inference pipeline. High-level descriptions:

- `lstm_sequencer.pt` — PyTorch LSTM-based sequence model used to assemble multi-day meal sequences and help maintain meal variety across days.
- `lgbm_*.pkl` — LightGBM models trained for specific optimization or classification tasks such as predicting safe substitutions, clinical suitability, or scoring meals for diabetes/hypertension/cholesterol-aware recommendations.
- `rf_safety.pkl` — Random Forest used as a safety filter to flag risky meal combinations for users with clinical conditions.
- `xgb_ranker.pkl` — XGBoost ranker used for ranking candidate meal options according to combined heuristics (taste, region, nutrition, safety).
- `meal_clusters.pkl` — Clustering artifact used to group similar recipes/meals to reduce repetition and ensure diversity.
- `preprocessors.pkl` — Feature preprocessors (scalers, encoders) used to transform user/profile inputs to model-ready features.
- `anomaly_detector.pkl` — Lightweight anomaly detection to catch out-of-range profiles or malformed inputs.

These models are used by the `DietInferenceEngine` implemented in `model_inference.py`. The engine composes scores and constraints from the models, applies rule-based safety checks, and returns a structured diet plan JSON used by the frontend.

Data Coverage
-------------

- The `datasets/` folder contains region-specific CSV datasets used to build and validate the planner. Each file corresponds to an Indian state or region (e.g., `kerala_diet_dataset_final.csv`, `punjab_diet_dataset_final.csv`, etc.).
- These datasets capture local recipes, ingredient lists, common preparation styles, and sample portion sizes to enable culturally relevant meal generation.
- The repository intentionally stores these CSVs to make model experiments reproducible. For production, consider using a curated, privacy-compliant dataset or remote storage.

Security & Secrets
------------------

- Keep sensitive credentials out of source control.
- The repository contains `.env.example` and `frontend/.env.example` templates. Copy these to `.env` (root) and `frontend/.env` locally and fill in values such as `MONGODB_URI` and `VITE_API_URL`.
- `.gitignore` is configured to ignore `.env`, `frontend/.env`, and other common env variants.

Environment Variables
---------------------

Backend (root `.env`):
- `MONGODB_URI` — MongoDB Atlas connection string (e.g. `mongodb+srv://...`).
- `SECRET_KEY` — optional app secret used for any cryptographic features.

Frontend (`frontend/.env` or Vercel env):
- `VITE_API_URL` — Public URL of the backend (e.g. `https://api.example.com`); frontend falls back to `http://localhost:8000` when not set.

Local Development
-----------------

1. Backend (Python / FastAPI)

```powershell
cd indie-dietyy
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

2. Frontend (Vite)

```powershell
cd frontend
npm install
npm run dev
# or for build: npm run build
```

Deployment Recommendations
--------------------------

Frontend
- Vercel is a good fit for the Vite frontend. Connect the GitHub repository and set the build command to `npm run build` and output `dist` (or use the default Vercel app settings). Add `VITE_API_URL` in Vercel's Environment Variables.

Backend
- This backend loads ML models into process memory and is stateful; serverless platforms (Vercel Serverless Functions) are not ideal. Recommended hosts:
  - Render / Railway / Fly.io — can run a persistent container or process that keeps models loaded.
  - Self-managed VPS / DigitalOcean — for full control if you expect high resource needs.
- Typical start command (Render/Generic):

```text
pip install -r requirements.txt
gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:$PORT
```

Connecting Frontend and Backend
-------------------------------

1. Deploy your backend to a public URL (e.g., `https://api.yourdomain.com`).
2. In Vercel (frontend project), set `VITE_API_URL` to that backend URL.
3. Ensure `app.py` CORS configuration allows your frontend origin. Currently it sets `allow_origins=["*"]` — change to your Vercel domain for production.

Notes and Caveats
-----------------

- Model sizes: some artifacts (e.g., `lstm_sequencer.pt`) may be large. If deploying on limited-memory instances, monitor memory usage.
- If you pushed sensitive data to any remote prior to removing `.env`, rotate secrets immediately.
- This project is intended as research/prototype code. Before production, add formal testing, model versioning, CI/CD safety checks, and a formal privacy / data retention policy.

Acknowledgements
----------------

Built with FastAPI, Vite, PyTorch, LightGBM and common ML toolkits. The front-end design is lightweight and intentionally dependency-free for simpler deploys.

Contributing
------------

Contributions are welcome. Please open issues for bugs or feature requests, and create PRs for improvements. Keep secrets out of PRs.

License
-------

This repository does not include a license file by default. Add a license if you plan to make this public under a specific license (e.g., MIT).
