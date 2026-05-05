from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime

from database import Database
from model_inference import DietInferenceEngine

# Initialize the global engine variable
engine: DietInferenceEngine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup Logic ---
    print("Starting up FastAPI Server...")
    
    # 1. Connect to Database
    await Database.connect_db()
    db = Database.get_db()
    
    # 2. Load ML Models (pass db so it can cache translations to MongoDB)
    global engine
    try:
        engine = DietInferenceEngine(db=db)
        print("✅ AI Models loaded into memory successfully!")
    except Exception as e:
        print(f"❌ Critical Error loading ML Models: {e}")
        
    yield # Server runs here
    
    # --- Shutdown Logic ---
    await Database.close_db()

# Create FastAPI app
app = FastAPI(
    title="Indie Dietyy ML Backend",
    description="Heavy AI Backend serving PyTorch & LightGBM inference",
    version="1.0.0",
    lifespan=lifespan
)

# Allow CORS for the Vercel Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Model
class UserProfile(BaseModel):
    user_id: Optional[str] = Field(default=None, description="Optional ID for logged in users")
    name: str = Field(default="Guest", description="User's Name")
    age: int = Field(default=30, description="User's Age")
    weight_kg: float = Field(default=70.0, description="Weight in kg")
    height_cm: float = Field(default=170.0, description="Height in cm")
    
    state: str = Field(..., description="Indian State (e.g. Kerala)")
    language: str = Field(default="en", description="Language code")
    
    diet_type: str = Field(..., description="Vegetarian, Non-Vegetarian, Both, or Vegan")
    meat_prefs: List[str] = Field(default_factory=list, description="Preferred meats if Non-Veg/Both")
    
    goal: str = Field(default="balanced", description="weight_loss, weight_gain, balanced")
    
    # Selected Medical Conditions
    conditions: List[str] = Field(default_factory=list, description="List of conditions e.g. ['diabetes', 'hypertension']")
    
    # Raw Medical Data
    blood_sugar: Optional[float] = Field(default=None, description="Fasting Blood Sugar mg/dL")
    systolic_bp: Optional[float] = Field(default=None, description="Systolic BP (Upper)")
    diastolic_bp: Optional[float] = Field(default=None, description="Diastolic BP (Lower)")
    cholesterol: Optional[float] = Field(default=None, description="Total Cholesterol mg/dL")
    
    allergies: str = Field(default="", description="Free text allergies")

@app.get("/")
async def root():
    return {"message": "Indie Dietyy ML Inference Server is online."}

@app.get("/api/health")
async def health_check():
    db = Database.get_db()
    db_status = "connected" if db is not None else "disconnected"
    engine_status = "loaded" if engine is not None else "failed"
    
    return {
        "status": "healthy",
        "database": db_status,
        "ai_engine": engine_status
    }

class TranslationRequest(BaseModel):
    texts: List[str]
    target_lang: str

@app.post("/api/translate")
async def translate_ui(req: TranslationRequest):
    global engine
    if engine is None:
        raise HTTPException(status_code=500, detail="AI Engine not loaded.")
    
    try:
        translated = {text: engine.translate(text, req.target_lang) for text in req.texts}
        return translated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_plan")
async def generate_plan(profile: UserProfile):
    global engine
    if engine is None:
        raise HTTPException(status_code=500, detail="AI Engine failed to load.")
        
    # Convert Pydantic model to dict
    profile_dict = profile.model_dump()
    
    try:
        # Run inference
        result = engine.generate_plan(profile_dict)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        # Save to MongoDB if a database connection exists
        db = Database.get_db()
        if db is not None:
            document = {
                "user_id": profile.user_id if profile.user_id else "anonymous",
                "profile": profile_dict,
                "plan": result["diet_plan"],
                "created_at": datetime.datetime.now(datetime.timezone.utc)
            }
            # Insert into 'generated_plans' collection asynchronously
            await db.generated_plans.insert_one(document)
            print(f"✅ Successfully saved generated plan to MongoDB for user: {document['user_id']}")
            
        # Flush any newly translated food names to MongoDB (best-effort)
        try:
            await engine.flush_translation_cache(db)
        except Exception as flush_err:
            print(f"[Non-critical] Translation cache flush failed: {flush_err}")

        return result
        
    except Exception as e:
        print(f"Inference Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # This allows you to run `python app.py` for local testing
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
