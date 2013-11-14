"""category.colour

Revision ID: f4c98b9a67f
Revises: 309391eabef6
Create Date: 2013-11-14 16:01:50.918212

"""

# revision identifiers, used by Alembic.
revision = 'f4c98b9a67f'
down_revision = '309391eabef6'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('category', sa.Column('colour', sa.String(length=8), nullable=True))


def downgrade():
    op.drop_column('category', 'colour')
