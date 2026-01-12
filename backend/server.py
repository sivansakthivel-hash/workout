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
import pandas as pd
import secrets
import openpyxl

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Excel file path
EXCEL_FILE = ROOT_DIR / "workout_app_data.xlsx"

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

# Initialize Excel file if not exists
def init_excel():
    if not EXCEL_FILE.exists():
        with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
            # Create users sheet
            users_df = pd.DataFrame(columns=['user_id', 'name', 'pin', 'created_at'])
            users_df.to_excel(writer, sheet_name='users', index=False)
            
            # Create workouts sheet
            workouts_df = pd.DataFrame(columns=['user_id', 'date', 'workout_done'])
            workouts_df.to_excel(writer, sheet_name='workouts', index=False)

def read_users():
    init_excel()
    df = pd.read_excel(EXCEL_FILE, sheet_name='users', dtype={'pin': str})
    return df

def read_workouts():
    init_excel()
    return pd.read_excel(EXCEL_FILE, sheet_name='workouts')

def write_to_excel(users_df, workouts_df):
    with pd.ExcelWriter(EXCEL_FILE, engine='openpyxl') as writer:
        users_df.to_excel(writer, sheet_name='users', index=False)
        workouts_df.to_excel(writer, sheet_name='workouts', index=False)

def calculate_streak(user_id: int, workouts_df: pd.DataFrame) -> int:
    # Get user's workouts sorted by date descending
    user_workouts = workouts_df[
        (workouts_df['user_id'] == user_id) & 
        (workouts_df['workout_done'] == True)
    ].copy()
    
    if user_workouts.empty:
        return 0
    
    # Convert date column to datetime
    user_workouts['date'] = pd.to_datetime(user_workouts['date'])
    user_workouts = user_workouts.sort_values('date', ascending=False)
    
    today = datetime.now().date()
    streak = 0
    expected_date = today
    
    for _, row in user_workouts.iterrows():
        workout_date = row['date'].date()
        
        if workout_date == expected_date:
            streak += 1
            expected_date = expected_date - timedelta(days=1)
        elif workout_date == expected_date + timedelta(days=1):
            # Allow checking yesterday as part of streak
            continue
        else:
            break
    
    return streak

@api_router.post("/register")
async def register(req: RegisterRequest, response: Response):
    users_df = read_users()
    workouts_df = read_workouts()
    
    # Check if user already exists
    if not users_df.empty and req.name in users_df['name'].values:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Validate PIN
    if len(req.pin) != 4 or not req.pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be exactly 4 digits")
    
    # Create new user
    new_user_id = 1 if users_df.empty else int(users_df['user_id'].max()) + 1
    new_user = pd.DataFrame([{
        'user_id': new_user_id,
        'name': req.name,
        'pin': req.pin,
        'created_at': datetime.now().isoformat()
    }])
    
    users_df = pd.concat([users_df, new_user], ignore_index=True)
    write_to_excel(users_df, workouts_df)
    
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
    users_df = read_users()
    
    # Find user - convert PIN to string for comparison
    user = users_df[
        (users_df['name'] == req.name) & 
        (users_df['pin'].astype(str) == req.pin)
    ]
    
    if user.empty:
        raise HTTPException(status_code=401, detail="Invalid name or PIN")
    
    user_id = int(user.iloc[0]['user_id'])
    name = user.iloc[0]['name']
    
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
    
    workouts_df = read_workouts()
    
    # Get user's workouts
    user_workouts = workouts_df[
        (workouts_df['user_id'] == user_id) & 
        (workouts_df['workout_done'] == True)
    ].copy()
    
    # Calculate stats
    today = datetime.now().date()
    today_str = today.isoformat()
    
    # Check if today is marked
    if not user_workouts.empty:
        user_workouts['date'] = pd.to_datetime(user_workouts['date']).dt.date
        today_marked = today in user_workouts['date'].values
    else:
        today_marked = False
    
    # Total workout days
    total_workout_days = len(user_workouts)
    
    # Last workout date
    if not user_workouts.empty:
        last_workout_date = user_workouts['date'].max().isoformat()
    else:
        last_workout_date = None
    
    # Current streak
    current_streak = calculate_streak(user_id, workouts_df)
    
    # Workout history (last 10)
    workout_history = []
    if not user_workouts.empty:
        user_workouts_sorted = user_workouts.sort_values('date', ascending=False).head(10)
        for _, row in user_workouts_sorted.iterrows():
            workout_history.append({
                'date': row['date'].isoformat(),
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
    
    users_df = read_users()
    workouts_df = read_workouts()
    
    # Calculate stats for all users
    leaderboard = []
    for _, user in users_df.iterrows():
        user_id = int(user['user_id'])
        name = user['name']
        
        # Calculate streak
        current_streak = calculate_streak(user_id, workouts_df)
        
        # Calculate total workout days
        user_workouts = workouts_df[
            (workouts_df['user_id'] == user_id) & 
            (workouts_df['workout_done'] == True)
        ]
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
    
    workouts_df = read_workouts()
    users_df = read_users()
    
    today = datetime.now().date()
    
    # Check if already marked today
    if not workouts_df.empty:
        workouts_df['date'] = pd.to_datetime(workouts_df['date']).dt.date
        already_marked = workouts_df[
            (workouts_df['user_id'] == user_id) & 
            (workouts_df['date'] == today) & 
            (workouts_df['workout_done'] == True)
        ]
        
        if not already_marked.empty:
            current_streak = calculate_streak(user_id, workouts_df)
            total_days = len(workouts_df[
                (workouts_df['user_id'] == user_id) & 
                (workouts_df['workout_done'] == True)
            ])
            return MarkWorkoutResponse(
                success=False,
                message="Workout already marked for today",
                streak=current_streak,
                total_days=total_days
            )
    
    # Add new workout entry
    new_workout = pd.DataFrame([{
        'user_id': user_id,
        'date': today.isoformat(),
        'workout_done': True
    }])
    
    workouts_df = read_workouts()  # Re-read to ensure fresh data
    workouts_df = pd.concat([workouts_df, new_workout], ignore_index=True)
    write_to_excel(users_df, workouts_df)
    
    # Calculate new stats
    current_streak = calculate_streak(user_id, workouts_df)
    total_days = len(workouts_df[
        (workouts_df['user_id'] == user_id) & 
        (workouts_df['workout_done'] == True)
    ])
    
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

# Initialize Excel on startup
@app.on_event("startup")
async def startup_event():
    init_excel()
    logger.info("Excel file initialized")
