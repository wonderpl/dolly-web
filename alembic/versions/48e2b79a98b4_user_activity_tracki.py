"""user_activity.tracking_code

Revision ID: 48e2b79a98b4
Revises: 143551ce8e91
Create Date: 2013-09-26 14:25:00.161762

"""

# revision identifiers, used by Alembic.
revision = '48e2b79a98b4'
down_revision = '143551ce8e91'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user_activity', sa.Column('tracking_code', sa.String(length=128), nullable=True))


def downgrade():
    op.drop_column('user_activity', 'tracking_code')
