"""add telegram fields

Revision ID: 001_add_telegram_fields
Revises: 
Create Date: 2023-12-23 09:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_add_telegram_fields'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns
    op.add_column('user', sa.Column('telegram_display_name', sa.String(), nullable=True))
    op.add_column('user', sa.Column('telegram_username', sa.String(), nullable=True))

def downgrade():
    # Remove columns
    op.drop_column('user', 'telegram_display_name')
    op.drop_column('user', 'telegram_username')