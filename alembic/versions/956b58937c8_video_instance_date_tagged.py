"""video_instance.date_tagged

Revision ID: 956b58937c8
Revises: 1b2516ccffcc
Create Date: 2014-03-24 16:15:20.966812

"""

# revision identifiers, used by Alembic.
revision = '956b58937c8'
down_revision = '1b2516ccffcc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('video_instance', sa.Column('date_tagged', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('video_instance', 'date_tagged')
