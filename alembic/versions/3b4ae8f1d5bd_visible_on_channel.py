"""visible on channel

Revision ID: 3b4ae8f1d5bd
Revises: 3e86fe829c0c
Create Date: 2013-06-12 15:39:02.820740

"""

# revision identifiers, used by Alembic.
revision = '3b4ae8f1d5bd'
down_revision = '3e86fe829c0c'

from alembic import op
import sqlalchemy as sa

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('channel', sa.Column('visible', sa.Boolean(), server_default='false', nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('channel', 'visible')
    ### end Alembic commands ###
