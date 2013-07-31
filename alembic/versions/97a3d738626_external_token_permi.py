"""external_token.permissions

Revision ID: 97a3d738626
Revises: 2465166e851f
Create Date: 2013-07-30 17:07:10.725968

"""

# revision identifiers, used by Alembic.
revision = '97a3d738626'
down_revision = '2465166e851f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('external_token', sa.Column('permissions', sa.String(length=1024), nullable=True))
    op.add_column('external_token', sa.Column('meta', sa.String(length=1024), nullable=True))


def downgrade():
    op.drop_column('external_token', 'permissions')
    op.drop_column('external_token', 'meta')
