# Simple Workout Streak Tracker

A simple full-stack web application for tracking daily workout streaks with user authentication.

## Features

- 👤 User registration and login with 4-digit PIN
- 💪 Daily workout tracking
- 🔥 Streak calculation
- 📊 Workout history
- 📱 Responsive modern UI
- 🎨 Dark mode design

## Tech Stack

**Backend:**
- FastAPI (Python)
- Pandas + OpenPyXL (Excel storage)
- Uvicorn (ASGI server)

**Frontend:**
- HTML5
- CSS3 (Modern dark theme with gradients)
- Vanilla JavaScript

## Quick Start with Docker

### Prerequisites
- Docker Desktop installed
- Docker Compose

### Setup and Run

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd workout

# 2. Setup environment variables
cp backend/.env.example backend/.env

# 3. Start the application
docker-compose up --build
```

**Access the application:**
- Application: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Stop the Application

```bash
# Stop services
docker-compose down

# Stop and remove data
docker-compose down -v
```

## Manual Setup (Without Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

Then open http://localhost:8000 in your browser.

## Project Structure

```
workout/
├── backend/
│   ├── server.py              # FastAPI application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Docker configuration
│   ├── static/               # Frontend files
│   │   ├── index.html        # Login/Register page
│   │   ├── dashboard.html    # Main app page
│   │   ├── css/
│   │   │   └── styles.css    # Styling
│   │   └── js/
│   │       └── app.js        # JavaScript utilities
│   └── .env.example          # Environment template
├── docker-compose.yml        # Docker orchestration
└── README.md
```

## API Endpoints

- `GET /` - Serve login/register page
- `POST /api/register` - Register new user
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/dashboard` - Get user dashboard data
- `POST /api/mark-workout` - Mark today's workout

## Environment Variables

### Backend (.env)
```bash
PORT=8000
```

## Docker Commands

```bash
# Start application
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up --build
```

## Data Persistence

Workout data is stored in an Excel file (`workout_app_data.xlsx`) and persisted using Docker volumes.

**Backup data:**
```bash
docker run --rm -v workout_workout-data:/data -v $(pwd):/backup alpine tar czf /backup/workout-data-backup.tar.gz -C /data .
```

**Restore data:**
```bash
docker run --rm -v workout_workout-data:/data -v $(pwd):/backup alpine tar xzf /backup/workout-data-backup.tar.gz -C /data
```

## Development

### Hot Reload
Code changes automatically trigger server restart in development mode.

### Testing
```bash
# Run backend tests
python backend_test.py
```

## Deployment

### Docker Deployment

1. Build the image:
```bash
docker-compose build
```

2. Deploy to your platform:
- AWS ECS
- DigitalOcean App Platform
- Google Cloud Run
- Azure Container Instances
- Any Docker-compatible platform

### Environment Setup

For production, create a `.env` file in the `backend/` directory with appropriate values.

## Security Notes

⚠️ **Important for Production:**
- Use HTTPS/SSL certificates
- Implement proper password hashing (currently using plain 4-digit PINs)
- Consider migrating from Excel to SQLite or PostgreSQL
- Add rate limiting on authentication endpoints
- Configure firewall rules
- Use environment-specific secrets management

## Features

### Authentication
- Simple 4-digit PIN authentication
- Cookie-based sessions
- Automatic redirect on logout

### Workout Tracking
- Mark daily workouts
- Prevent duplicate entries for same day
- Automatic streak calculation
- Workout history with last 10 entries

### UI/UX
- Modern dark theme with gradients
- Smooth animations and transitions
- Responsive design (mobile-friendly)
- Real-time updates
- Clean, intuitive interface

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - feel free to use this project for learning or personal use.

## Support

For issues or questions, please open an issue on GitHub.

---

**Built with ❤️ using FastAPI and Vanilla JavaScript**
