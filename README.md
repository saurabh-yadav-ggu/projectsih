# Shield AI - Sovereign AI Platform

Shield AI is a full-stack AI platform built with a FastAPI backend and a React (Vite) frontend.

## Folder Structure

```
.
├── backend/
│   ├── app/                  # Application source code
│   │   ├── core/             # Security, auth, & JWT handlers
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── routers/          # FastAPI API routes (auth, chat, etc.)
│   │   ├── schemas/          # Pydantic data schemas
│   │   ├── services/         # Business logic services
│   │   ├── database.py       # DB engine & session configuration
│   │   └── main.py           # FastAPI application entry point
│   ├── database/             # SQLite storage directory
│   ├── .env.example          # Backend environment variables template
│   ├── pyproject.toml        # Python project configuration
│   └── requirements.txt      # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/              # Centralized API service methods
│   │   ├── assets/           # Static images & icons
│   │   ├── components/       # Modular UI components
│   │   │   ├── auth/         # Login & Registration modal components
│   │   │   ├── chat/         # Chat input & Quick tasks components
│   │   │   └── layout/       # Sidebar, TopBar, & Footer layouts
│   │   ├── App.jsx           # Main application container
│   │   ├── index.css         # Global CSS design system
│   │   └── main.jsx          # React app entry point
│   ├── public/               # Public assets
│   ├── .env.example          # Frontend environment variables template
│   ├── package.json          # Node dependencies & scripts
│   └── vite.config.js        # Vite bundler configuration
└── README.md
```

## Quick Start

### Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.
