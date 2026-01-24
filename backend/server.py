from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi import FastAPI, APIRouter, HTTPException, Cookie, Response, UploadFile, File
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
import io
import zipfile
import shutil
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

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
    try:
        if os.path.exists(USERS_FILE) and os.path.getsize(USERS_FILE) > 0:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return []

def read_workouts():
    """Read workouts from JSON file"""
    init_data()
    try:
        if os.path.exists(WORKOUTS_FILE) and os.path.getsize(WORKOUTS_FILE) > 0:
            with open(WORKOUTS_FILE, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return []

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
    
    # Workout history (all for calendar)
    workout_history = []
    if user_workouts:
        for workout in user_workouts:
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

class MarkWorkoutRequest(BaseModel):
    date: Optional[str] = None

@api_router.post("/mark-workout", response_model=MarkWorkoutResponse)
async def mark_workout(req: MarkWorkoutRequest = MarkWorkoutRequest(), session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = sessions[session_id]
    user_id = user_data['user_id']
    
    workouts = read_workouts()
    
    # Use requested date or today
    if req.date:
        try:
            target_date = datetime.fromisoformat(req.date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
        
    target_date_str = target_date.isoformat()
    today = datetime.now().date()
    
    # Prevent marking future dates
    if target_date > today:
        raise HTTPException(status_code=400, detail="Cannot mark workouts for future dates")
    
    # Check if already marked
    already_marked = any(w['user_id'] == user_id and w['date'] == target_date_str and w['workout_done'] for w in workouts)
    
    if already_marked:
        current_streak = calculate_streak(user_id, workouts)
        total_days = len([w for w in workouts if w['user_id'] == user_id and w['workout_done']])
        return MarkWorkoutResponse(
            success=False,
            message=f"Workout already marked for {target_date_str}",
            streak=current_streak,
            total_days=total_days
        )
    
    # Add new workout entry
    new_workout = {
        'user_id': user_id,
        'date': target_date_str,
        'workout_done': True
    }
    
    workouts.append(new_workout)
    save_workouts(workouts)
    
    # Calculate new stats
    current_streak = calculate_streak(user_id, workouts)
    total_days = len([w for w in workouts if w['user_id'] == user_id and w['workout_done']])
    
    date_label = "today" if target_date == today else target_date_str
    return MarkWorkoutResponse(
        success=True,
        message=f"Workout marked for {date_label}!",
        streak=current_streak,
        total_days=total_days
    )

@api_router.post("/unmark-workout", response_model=MarkWorkoutResponse)
async def unmark_workout(req: MarkWorkoutRequest, session_id: Optional[str] = Cookie(None)):
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_data = sessions[session_id]
    user_id = user_data['user_id']
    
    if not req.date:
        raise HTTPException(status_code=400, detail="Date is required to unmark")
    
    workouts = read_workouts()
    
    # Filter out the specific workout
    original_len = len(workouts)
    workouts = [w for w in workouts if not (w['user_id'] == user_id and w['date'] == req.date)]
    
    if len(workouts) == original_len:
        current_streak = calculate_streak(user_id, workouts)
        total_days = len([w for w in workouts if w['user_id'] == user_id and w['workout_done']])
        return MarkWorkoutResponse(
            success=False,
            message="No workout found for this date",
            streak=current_streak,
            total_days=total_days
        )
        
    save_workouts(workouts)
    
    # Calculate new stats
    current_streak = calculate_streak(user_id, workouts)
    total_days = len([w for w in workouts if w['user_id'] == user_id and w['workout_done']])
    
    return MarkWorkoutResponse(
        success=True,
        message=f"Workout removed for {req.date}!",
        streak=current_streak,
        total_days=total_days
    )

@api_router.get("/data/download")
async def download_data():
    """Download all data files as a zip archive"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if USERS_FILE.exists():
            z.write(USERS_FILE, arcname="users.json")
        if WORKOUTS_FILE.exists():
            z.write(WORKOUTS_FILE, arcname="workouts.json")
    
    buf.seek(0)
    return StreamingResponse(
        buf, 
        media_type="application/zip", 
        headers={"Content-Disposition": "attachment; filename=workout_tracker_backup.zip"}
    )

@api_router.post("/data/upload")
async def upload_data(file: UploadFile = File(...)):
    """Upload and replace data files from a zip archive"""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")
    
    try:
        contents = await file.read()
        buf = io.BytesIO(contents)
        
        with zipfile.ZipFile(buf, "r") as z:
            # Check for required files
            zip_names = z.namelist()
            if "users.json" not in zip_names and "workouts.json" not in zip_names:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid backup: Zip must contain users.json or workouts.json"
                )
            
            # Extract and replace
            if "users.json" in zip_names:
                z.extract("users.json", path=DATA_DIR)
            if "workouts.json" in zip_names:
                z.extract("workouts.json", path=DATA_DIR)
            
        # Clear active sessions to prevent state issues with new data
        sessions.clear()
        return {"success": True, "message": "Data successfully restored. Please re-login."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

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

@app.get("/data-admin")
async def get_data_admin():
    return FileResponse(ROOT_DIR / "static" / "data-admin.html")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Background Tasks Logic
async def ping_home_endpoint():
    """Background task to hit the home endpoint every hour"""
    async with httpx.AsyncClient() as client:
        try:
            # We use localhost:8000 as it's internal to the container
            response = await client.get("https://workout-t9mo.onrender.com/")
            logger.info(f"Hourly self-ping status: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to ping home endpoint: {e}")

async def daily_backup_and_email():
    """Background task to zip data and email it every day"""
    try:
        # Create Zip in memory
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            if USERS_FILE.exists():
                z.write(USERS_FILE, arcname="users.json")
            if WORKOUTS_FILE.exists():
                z.write(WORKOUTS_FILE, arcname="workouts.json")
        
        zip_data = buf.getvalue()
        
        # Email configuration from environment
        recipient = "sivanhash@gmail.com"
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        
        if not smtp_user or not smtp_pass:
            logger.warning("SMTP credentials (SMTP_USER/SMTP_PASS) not set. Daily backup email skipped.")
            return

        # Prepare Email
        msg = MIMEMultipart()
        msg['Subject'] = f"Workout Tracker Backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg['From'] = smtp_user
        msg['To'] = recipient
        
        msg.attach(MIMEText("Attached is the daily backup of the workout tracker data files (users and workouts).", 'plain'))
        
        attachment = MIMEApplication(zip_data, Name="backup.zip")
        attachment['Content-Disposition'] = 'attachment; filename="workout_data_backup.zip"'
        msg.attach(attachment)
        
        # Send Email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        logger.info(f"Daily backup successfully emailed to {recipient}")
    except Exception as e:
        logger.error(f"Failed to perform daily backup/email: {e}")

# Initialize Data and Tasks on startup
@app.on_event("startup")
async def startup_event():
    init_data()
    logger.info("JSON data initialized")
    
    # Initialize Scheduler
    scheduler = AsyncIOScheduler()
    
    # Task 1: Hit home endpoint every 5 minutes
    scheduler.add_job(ping_home_endpoint, 'interval', minutes=1, id='ping_task')
    
    # Task 2: Backup and email every day
    scheduler.add_job(daily_backup_and_email, 'interval', days=1, id='backup_task')
    
    scheduler.start()
    logger.info("Background scheduler started (Ping & Backup tasks)")
