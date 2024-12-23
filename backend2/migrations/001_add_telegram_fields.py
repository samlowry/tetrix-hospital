from sqlalchemy import Column, String, text
from alembic import op
import sqlalchemy as sa
import aiohttp
import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

async def get_telegram_info(telegram_id: int) -> tuple:
    """Get user's display name and username via Bot API"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return None, None
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={'chat_id': telegram_id}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        result = data['result']
                        first_name = result.get('first_name', '')
                        last_name = result.get('last_name', '')
                        display_name = f"{first_name} {last_name}".strip()
                        username = result.get('username')
                        return display_name or None, username
    except Exception:
        pass
    return None, None

async def upgrade_data():
    """Update existing users with Telegram info"""
    from models.database import async_session
    from models.user import User
    
    async with async_session() as session:
        # Get all users
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        # Update each user's telegram info
        for user in users:
            display_name, username = await get_telegram_info(user.telegram_id)
            if display_name or username:
                user.telegram_display_name = display_name
                user.telegram_username = username
        
        await session.commit()

def upgrade():
    # Add new columns
    op.add_column('user', Column('telegram_display_name', String, nullable=True))
    op.add_column('user', Column('telegram_username', String, nullable=True))
    
    # Run async upgrade
    asyncio.run(upgrade_data())

def downgrade():
    # Remove columns
    op.drop_column('user', 'telegram_display_name')
    op.drop_column('user', 'telegram_username') 