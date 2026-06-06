# backend/app.py
import sys
import os

# Make the project root importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import router

app = FastAPI(
    title="F1 Supply Chain & Race Strategy Optimizer API",
    description=(
        "Phase 5 API Layer — exposes MDP strategy solving and Monte Carlo "
        "simulation results for the F1 Race Strategy dashboard."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow the React dev server (port 3000) and any localhost origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok", "service": "F1 Strategy Optimizer API"}
