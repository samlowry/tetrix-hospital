"""update telegram data

Revision ID: 002_update_telegram_data
Revises: 001_add_telegram_fields
Create Date: 2023-12-23 09:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
import requests
import os


# revision identifiers, used by Alembic.
revision = '002_update_telegram_data'
down_revision = '001_add_telegram_fields'
branch_labels = None
depends_on = None


def get_telegram_info(telegram_id: int) -> tuple:
    """Get user's display name and username via Bot API"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return None, None
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        response = requests.get(url, params={'chat_id': telegram_id})
        if response.status_code == 200:
            data = response.json()
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


def upgrade():
    # Get database connection
    conn = op.get_bind()
    
    # Get all users
    users = conn.execute(sa.text('SELECT telegram_id FROM "user"')).fetchall()
    
    # Update each user's telegram info
    for (telegram_id,) in users:
        display_name, username = get_telegram_info(telegram_id)
        if display_name or username:
            conn.execute(
                sa.text('UPDATE "user" SET telegram_display_name = :name, telegram_username = :username WHERE telegram_id = :tid'),
                {'name': display_name, 'username': username, 'tid': telegram_id}
            )


def downgrade():
    # Nothing to do here
    pass