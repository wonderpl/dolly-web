"""user.profile_cover

Revision ID: 2872f85c3170
Revises: 3103dc7dcaa3
Create Date: 2013-10-21 14:53:55.093966

"""

# revision identifiers, used by Alembic.
revision = '2872f85c3170'
down_revision = '3103dc7dcaa3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('user', sa.Column('profile_cover', sa.String(length=1024)))
    op.add_column('user', sa.Column('brand_profile_cover', sa.String(length=1024)))


def downgrade():
    op.drop_column('user', 'profile_cover')
    op.drop_column('user', 'brand_profile_cover')
