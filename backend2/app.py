from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
import logging
import alembic.config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

# Routers
from routers import telegram, ton_connect, api
from models.database import init_db, engine

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

async def check_migrations_needed() -> bool:
    """Check if there are any pending migrations"""
    try:
        # Get current database version
        async with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
        
        # Get latest available version
        config = alembic.config.Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        head_rev = script.get_current_head()
        
        # Compare versions
        if current_rev != head_rev:
            logger.info(f"Database migration needed: current={current_rev}, target={head_rev}")
            return True
        else:
            logger.info("Database is up to date")
            return False
            
    except Exception as e:
        logger.warning(f"Error checking migrations: {e}")
        # If we can't check, better to run migrations to be safe
        return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    
    # Check and run migrations if needed
    if await check_migrations_needed():
        logger.info("Running database migrations...")
        alembic.config.main(argv=['upgrade', 'head'])
    
    # Initialize database
    logger.info("Initializing database...")
    await init_db()  # Create tables if they don't exist
    
    await telegram.setup_webhook()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    pass

# Create FastAPI application
app = FastAPI(
    title="Tetrix Hospital Bot",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tryItOutEnabled": True,
        "displayRequestDuration": True
    }
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