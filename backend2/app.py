import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import (
    FRONTEND_URL, FASTAPI_HOST, FASTAPI_PORT,
    DATABASE_URL
)
from routers import ton_connect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TETRIX Bot API",
    description="API for TETRIX Token Bot System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
)

# Include routers
app.include_router(ton_connect.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        reload=True
    ) 