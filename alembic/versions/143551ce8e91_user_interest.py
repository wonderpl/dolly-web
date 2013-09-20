"""user_interest

Revision ID: 143551ce8e91
Revises: 52303a73e60c
Create Date: 2013-09-13 11:32:42.188235

"""

# revision identifiers, used by Alembic.
revision = '143551ce8e91'
down_revision = '52303a73e60c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user_interest',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('explicit', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('category', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint('user_interest_uniq', 'user_interest',
                                ['user', 'explicit', 'category'])
    op.create_index('user_interest_category', 'user_interest', ['category'])


def downgrade():
    op.drop_table('user_interest')
