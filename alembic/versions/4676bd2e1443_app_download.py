"""app_download

Revision ID: 4676bd2e1443
Revises: 13640a8393c3
Create Date: 2013-08-19 17:30:09.545090

"""

# revision identifiers, used by Alembic.
revision = '4676bd2e1443'
down_revision = '13640a8393c3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'app_download',
        sa.Column('source', sa.Enum('itunes', 'playstore', name='app_download_source'), nullable=False),
        sa.Column('version', sa.String(length=16), nullable=False),
        sa.Column('action', sa.Enum('download', 'update', name='app_download_action'), nullable=False),
        sa.Column('country', sa.CHAR(length=2), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('count', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('source', 'version', 'action', 'country', 'date')
    )


def downgrade():
    op.drop_table('app_download')
