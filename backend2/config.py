# Standard library imports for system operations and logging
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up application logging configuration
logger = logging.getLogger(__name__)

# Load environment variables from .env file into application
load_dotenv()

# FastAPI server configuration settings
FASTAPI_HOST = os.getenv('FASTAPI_HOST', '0.0.0.0')  # Host address for FastAPI server
FASTAPI_PORT = int(os.getenv('FASTAPI_PORT', 5000))  # Port number for FastAPI server
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')  # URL of the frontend application

# Telegram webhook configuration
# Unique path for Telegram webhook endpoint with random suffix for security
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

# Redis cache configuration
REDIS_PORT = 6379  # Standard Redis port number
REDIS_HOST = 'redis'  # Redis server hostname
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"  # Complete Redis connection URL

# PostgreSQL database configuration
POSTGRES_USER = os.getenv('POSTGRES_USER', 'tetrix')  # Database username
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'tetrixpass')  # Database password
POSTGRES_DB = os.getenv('POSTGRES_DB', 'tetrix')  # Database name
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')  # Database host
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))  # Database port

# AsyncPG database connection URL
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Telegram bot configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Authentication token for Telegram bot
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# Webhook URL configuration for Telegram bot
BACKEND_URL = os.getenv('BACKEND_URL')  # Base URL of the backend server
if not BACKEND_URL:
    raise ValueError("BACKEND_URL environment variable is required")
WEBHOOK_URL = f"{BACKEND_URL}{WEBHOOK_PATH}"  # Complete webhook URL for Telegram
logger.info(f"Using webhook URL: {WEBHOOK_URL}")

# JWT authentication configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default-secret-key')  # Secret key for JWT encoding
JWT_ALGORITHM = 'HS256'  # Algorithm used for JWT encoding
JWT_EXPIRATION_DAYS = 30  # JWT token validity period in days

# TON blockchain configuration
TETRIX_CONTRACT_ADDRESS = os.getenv('TETRIX_CONTRACT_ADDRESS')  # Address of the Tetrix smart contract

# Application security constants
ALLOWED_DOMAINS = {'localhost', 'app.tetrix.xyz'}  # List of authorized domains
VALID_AUTH_TIME = 300  # Time window for TON proof validation in seconds