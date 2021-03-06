"""channel promotion table

Revision ID: 435343b23cef
Revises: e04431ae758
Create Date: 2013-07-02 13:44:39.592969

"""

# revision identifiers, used by Alembic.
revision = '435343b23cef'
down_revision = 'e04431ae758'

from alembic import op
import sqlalchemy as sa

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('channel_promotion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('channel', sa.CHAR(length=24), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('category', sa.Integer(), nullable=True),
    sa.Column('date_added', sa.DateTime(), nullable=False),
    sa.Column('date_updated', sa.DateTime(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('date_start', sa.DateTime(), nullable=False),
    sa.Column('date_end', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['channel'], ['channel.id'], ),
    sa.ForeignKeyConstraint(['locale'], ['locale.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    op.drop_table('channel_promotion')
    ### end Alembic commands ###
