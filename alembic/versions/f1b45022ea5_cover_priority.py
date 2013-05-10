"""cover priority

Revision ID: f1b45022ea5
Revises: 48e3bc6b039e
Create Date: 2013-05-10 16:03:32.751324

"""

# revision identifiers, used by Alembic.
revision = 'f1b45022ea5'
down_revision = '48e3bc6b039e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('rockpack_cover_art', sa.Column('priority', sa.Integer(), server_default='0', nullable=False))
    op.add_column('rockpack_cover_art', sa.Column('attribution', sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column('rockpack_cover_art', 'attribution')
    op.drop_column('rockpack_cover_art', 'priority')
