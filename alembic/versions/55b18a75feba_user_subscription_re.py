"""user_subscription_recommendation

Revision ID: 55b18a75feba
Revises: 2b0c3f05d150
Create Date: 2013-11-26 20:20:02.484846

"""

# revision identifiers, used by Alembic.
revision = '55b18a75feba'
down_revision = '2b0c3f05d150'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user_subscription_recommendation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('category', sa.Integer(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('filter', sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(['category'], ['category.id'], ),
        sa.ForeignKeyConstraint(['user'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('user_subscription_recommendation')
