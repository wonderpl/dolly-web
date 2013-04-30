"""channel boost and favourite

Revision ID: 48e3bc6b039e
Revises: 2d2011626632
Create Date: 2013-04-30 12:06:17.299494

"""

# revision identifiers, used by Alembic.
revision = '48e3bc6b039e'
down_revision = '2d2011626632'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('channel', sa.Column('editorial_boost', sa.Float(precision=1), server_default='1.0', nullable=True))
    op.add_column('channel', sa.Column('favourite', sa.Boolean(), server_default='false', nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('channel', 'favourite')
    op.drop_column('channel', 'editorial_boost')
    ### end Alembic commands ###
