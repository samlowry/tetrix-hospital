from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from http import HTTPStatus
import uvicorn
import os
from dotenv import load_dotenv
from bot_manager import BotManager
from config import WEBHOOK_URL

load_dotenv()

# Initialize bot manager
bot_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_manager
    # Initialize bot manager and set webhook
    bot_manager = BotManager(
        token=os.getenv('TELEGRAM_BOT_TOKEN'),
        db=None,  # We'll update this later
        User=None,  # We'll update this later
        ton_client=None,  # We'll update this later
        app=app
    )
    await bot_manager.application.bot.setWebhook(WEBHOOK_URL)
    async with bot_manager.application:
        await bot_manager.application.start()
        yield
        await bot_manager.application.stop()

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming Telegram webhook updates"""
    update_dict = await request.json()
    await bot_manager.application.update_queue.put(update_dict)
    return Response(status_code=HTTPStatus.OK)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 