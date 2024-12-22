from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
import logging

# Routers
from routers import telegram, ton_connect, api
from models.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all logs
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Set log levels for specific loggers
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

# Get our logger
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    await init_db()  # Create tables if they don't exist
    await telegram.setup_webhook()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    pass

# Create FastAPI application
app = FastAPI(
    title="Tetrix Hospital Bot",
    lifespan=lifespan
)

# Configure CORS for web application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Connect routers
app.include_router(telegram.router)  # Telegram bot
app.include_router(ton_connect.router)  # TON Connect authorization
app.include_router(api.router)  # API for partner application

# Test endpoint
@app.get("/")
async def root():
    return {"status": "ok", "message": "Tetrix Hospital Bot is running"}

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="debug"  # Set Uvicorn log level to debug
    ) 