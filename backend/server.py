from fastapi import FastAPI, APIRouter, HTTPException, Cookie, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, timedelta
import secrets
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Data directory and JSON file paths
DATA_DIR = ROOT_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
WORKOUTS_FILE = DATA_DIR / "workouts.json"

# In-memory session storage
sessions = {}

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class RegisterRequest(BaseModel):
    name: str
    pin: str

class LoginRequest(BaseModel):
    name: str
    pin: str

class MarkWorkoutResponse(BaseModel):
    success: bool
    message: str
    streak: int
    total_days: int

class DashboardResponse(BaseModel):
    name: str
    today_date: str
    current_streak: int
    total_workout_days: int
    last_workout_date: Optional[str]
    today_marked: bool
    workout_history: list

class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    current_streak: int
    total_workout_days: int
    is_current_user: bool = False

# Initialize JSON files if not exists
def init_data():
    """Initialize data directory and JSON files"""
    DATA_DIR.mkdir(exist_ok=True)
    
    if not USERS_FILE.exists():
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    
    if not WORKOUTS_FILE.exists():
        with open(WORKOUTS_FILE, 'w') as f:
            json.dump([], f)

def read_users():
    """Read users from JSON file"""
    init_data()
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def read_workouts():
    """Read workouts from JSON file"""
    init_data()
    with open(WORKOUTS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    """Save users to JSON file"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def save_workouts(workouts):
    """Save workouts to JSON file"""
    with open(WORKOUTS_FILE, 'w') as f:
        json.dump(workouts, f, indent=4)

def calculate_streak(user_id: int, workouts: list) -> int:
    """Calculate current workout streak for a user"""
    # Get user's workouts sorted by date descending
    user_workouts = [w for w in workouts if w['user_id'] == user_id and w['workout_done']]
    
    if not user_workouts:
        return 0
    
    # Sort by date descending
    user_workouts.sort(key=lambda x: x['date'], reverse=True)
    
    today = datetime.now().date()
    streak = 0
    expected_date = today
    
    for workout in user_workouts:
        workout_date = datetime.fromisoformat(workout['date']).date()
        
        if workout_date == expected_date:
            streak += 1
            expected_date = expected_date - timedelta(days=1)
        elif workout_date == expected_date + timedelta(days=1):
            # Allow checking yesterday as part of streak (if today isn't marked yet)
            continue
        elif workout_date > expected_date:
            # Skip future dates if any (shouldn't happen)
            continue
        else:
            # Gap in streak
            break
    
    return streak

@api_router.post("/register")
async def register(req: RegisterRequest, response: Response):
    users = read_users()
    
    # Check if user already exists
    if any(u['name'] == req.name for u in users):
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Validate PIN
    if len(req.pin) != 4 or not req.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    
    # Create new user
    new_user_id = 1 if not users else max(u['user_id'] for u in users) + 1
    new_user = {
        'user_id': new_user_id,
        'name': req.name,
        'pin': req.pin,
        'created_at': datetime.now().isoformat()
    }
    
    users.append(new_user)
    save_users(users)
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {'user_id': new_user_id, 'name': req.name}
    
    # Set cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400 * 30,  # 30 days
        samesite="lax"
    )
    
    return {"success": True, "message": "Registration successful", "name": req.name}

@api_router.post("/login")
async def login(req: LoginRequest, response: Response):
    users = read_users()
    
    # Find user
    user = next((u for u in users if u['name'] == req.name and str(u['pin']) == req.pin), None)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid name or PIN")
    
    user_id = user['user_id']
    name = user['name']
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {'user_id': user_id, 'name': name}
    
    # Set cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400 * 30,  # 30 days
        samesite="lax"
    )
    
    return {"success": True, "message": "Login successful", "name": name}

@api_router.post("/logout")
async def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response.delete_cookie(key="session_id")
    return {"success": True, "message": "Logged out successfully"}

@api_router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = sessions[session_id]
    user_id = user_data['user_id']
    name = user_data['name']
    
    workouts = read_workouts()
    
    # Get user's workouts
    user_workouts = [w for w in workouts if w['user_id'] == user_id and w['workout_done']]
    
    # Calculate stats
    today = datetime.now().date()
    today_str = today.isoformat()
    
    # Check if today is marked
    today_marked = any(w['date'] == today_str for w in user_workouts)
    
    # Total workout days
    total_workout_days = len(user_workouts)
    
    # Last workout date
    if user_workouts:
        # Sort by date descending
        user_workouts.sort(key=lambda x: x['date'], reverse=True)
        last_workout_date = user_workouts[0]['date']
    else:
        last_workout_date = None
    
    # Current streak
    current_streak = calculate_streak(user_id, workouts)
    
    # Workout history (last 10)
    workout_history = []
    if user_workouts:
        # Already sorted above
        for workout in user_workouts[:10]:
            workout_history.append({
                'date': workout['date'],
                'status': 'Completed'
            })
    
    return DashboardResponse(
        name=name,
        today_date=today_str,
        current_streak=current_streak,
        total_workout_days=total_workout_days,
        last_workout_date=last_workout_date,
        today_marked=today_marked,
        workout_history=workout_history
    )

@api_router.get("/leaderboard")
async def get_leaderboard(session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    current_user_id = sessions[session_id]['user_id']
    
    users = read_users()
    workouts = read_workouts()
    
    # Calculate stats for all users
    leaderboard = []
    for user in users:
        user_id = user['user_id']
        name = user['name']
        
        # Calculate streak
        current_streak = calculate_streak(user_id, workouts)
        
        # Calculate total workout days
        user_workouts = [w for w in workouts if w['user_id'] == user_id and w['workout_done']]
        total_workout_days = len(user_workouts)
        
        # Only include users with at least 1 streak or 1 workout day
        if current_streak > 0 or total_workout_days > 0:
            leaderboard.append({
                'user_id': user_id,
                'name': name,
                'current_streak': current_streak,
                'total_workout_days': total_workout_days,
                'is_current_user': user_id == current_user_id
            })
    
    # Sort by streak (descending), then by total days (descending)
    leaderboard.sort(key=lambda x: (x['current_streak'], x['total_workout_days']), reverse=True)
    
    # Add ranks
    for idx, entry in enumerate(leaderboard, 1):
        entry['rank'] = idx
        del entry['user_id']  # Remove user_id from response
    
    return leaderboard

@api_router.post("/mark-workout", response_model=MarkWorkoutResponse)
async def mark_workout(session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = sessions[session_id]
    user_id = user_data['user_id']
    
    workouts = read_workouts()
    
    today = datetime.now().date()
    today_str = today.isoformat()
    
    # Check if already marked today
    already_marked = any(w['user_id'] == user_id and w['date'] == today_str and w['workout_done'] for w in workouts)
    
    if already_marked:
        current_streak = calculate_streak(user_id, workouts)
        total_days = len([w for w in workouts if w['user_id'] == user_id and w['workout_done']])
        return MarkWorkoutResponse(
            success=False,
            message="Workout already marked for today",
            streak=current_streak,
            total_days=total_days
        )
    
    # Add new workout entry
    new_workout = {
        'user_id': user_id,
        'date': today_str,
        'workout_done': True
    }
    
    workouts.append(new_workout)
    save_workouts(workouts)
    
    # Calculate new stats
    current_streak = calculate_streak(user_id, workouts)
    total_days = len([w for w in workouts if w['user_id'] == user_id and w['workout_done']])
    
    return MarkWorkoutResponse(
        success=True,
        message="Workout marked successfully!",
        streak=current_streak,
        total_days=total_days
    )

# Include the router in the main app
app.include_router(api_router)

# Simplified CORS for same-origin (static files served from same server)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # Same origin, so this is safe
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")

# Serve index.html at root
@app.get("/")
async def read_root():
    return FileResponse(ROOT_DIR / "static" / "index.html")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Data on startup
@app.on_event("startup")
async def startup_event():
    init_data()
    logger.info("JSON data initialized")
