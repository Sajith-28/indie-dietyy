# Deploying the Backend (recommended: Render)

This document explains how to deploy the FastAPI backend using Render (recommended) or any container host that runs Docker.

Recommended: Render (quick, free-ish tier)
------------------------------------------------

1. Create a Render account and connect your GitHub repository (https://render.com).

2. Create a new **Web Service** and choose the `indie-dietyy` repository and the `main` branch.

3. Choose "Docker" as the environment (the repo contains a `Dockerfile`), or choose "Python" and set the Build & Start commands manually.

   - If using Docker (Render will use the `Dockerfile`): no extra build command required.
   - If using Python (Render's Python environment):
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:$PORT`

4. Add the required Environment Variables in the Render dashboard for the service:
   - `MONGODB_URI` — your MongoDB Atlas connection string (e.g. `mongodb+srv://<user>:<pass>@cluster0.mongodb.net/?retryWrites=true&w=majority`)
   - `SECRET_KEY` — a random secret string for any app cryptography (optional)

5. Set the instance plan (Start with `Starter` or `Free` if available) and create the service. Render will build your Docker image and deploy it.

6. After deployment, note the service URL (e.g., `https://indie-dietyy.onrender.com`).

7. In Vercel (frontend project settings) add `VITE_API_URL` with the backend public URL.

Alternative hosts
------------------
- Railway / Fly.io: similar process using Docker or direct Python deployments.
- VPS / Docker host: build and run the Docker image yourself:

```bash
docker build -t indie-dietyy-backend .
docker run -p 8000:8000 -e MONGODB_URI="your_mongo_uri" indie-dietyy-backend
```

Notes
-----
- The backend loads ML models into memory; choose an instance with sufficient RAM. Monitor memory after first deploy.
- Keep secrets in the Render environment settings; do not commit `.env`.
- If you want, I can prepare a GitHub Actions workflow to deploy automatically to Render when you push to `main` — you'll need to add a Render API key as a GitHub secret.
