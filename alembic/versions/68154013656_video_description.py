"""video.description

Revision ID: 68154013656
Revises: 834ff2d187
Create Date: 2014-04-03 17:02:46.921648

"""

# revision identifiers, used by Alembic.
revision = '68154013656'
down_revision = '834ff2d187'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('video', sa.Column('description', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('video', 'description')
