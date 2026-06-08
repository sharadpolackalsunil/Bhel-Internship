import os
import sys
import json
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scraper.scraper import create_driver
from scraper.profile_scraper import login_and_scrape_profile
from captcha_model.predict import CaptchaSolver

app = FastAPI(title="MITS Portal API", description="Live scraping API for BHEL Project")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global solver instance (loads on startup)
solver = None

@app.on_event("startup")
async def startup_event():
    global solver
    print("Initializing API...")
    print("Loading TrOCR Model into memory...")
    solver = CaptchaSolver()
    print("TrOCR Model loaded successfully.")

class LoginRequest(BaseModel):
    enrollment: str
    password: str

@app.post("/api/login")
async def login(request: LoginRequest):
    enrollment = request.enrollment.strip().upper()
    password = request.password.strip()
    
    # 1. Check Cache first
    profiles_dir = os.path.join(project_root, 'data', 'profiles')
    os.makedirs(profiles_dir, exist_ok=True)
    cache_path = os.path.join(profiles_dir, f"profile_{enrollment}.json")
    
    if os.path.exists(cache_path):
        print(f"[{enrollment}] Returning cached profile.")
        with open(cache_path, 'r', encoding='utf-8') as f:
            return {"status": "success", "source": "cache", "data": json.load(f)}
            
    # 2. Run Live Scraper
    print(f"[{enrollment}] Starting live scrape...")
    driver = None
    try:
        driver = create_driver(headless=True)
        # Note: If login_and_scrape_profile returns None, login failed
        data = login_and_scrape_profile(driver, solver, enrollment, password)
        
        if data is None:
            raise HTTPException(status_code=401, detail="Invalid credentials or CAPTCHA failed too many times.")
            
        return {"status": "success", "source": "live", "data": data}
        
    except Exception as e:
        print(f"[{enrollment}] Scrape Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if driver:
            driver.quit()

@app.get("/api/profile/{enrollment}")
async def get_student_profile(enrollment: str):
    """
    Returns the cached profile for a student if they have logged in before.
    This is used by the Admin dashboard to view live-scraped personal details.
    """
    enrollment = enrollment.strip().upper()
    cache_path = os.path.join(PROFILE_DIR, f"profile_{enrollment}.json")
    
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    
    # If not found, return 404
    raise HTTPException(status_code=404, detail="Profile not found in cache")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
