"""share link

Revision ID: 6e834dba68f
Revises: 184815d483a3
Create Date: 2013-05-01 11:54:57.961551

"""

# revision identifiers, used by Alembic.
revision = '6e834dba68f'
down_revision = '184815d483a3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'share_link',
        sa.Column('id', sa.String(length=8), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.Column('object_type', sa.String(length=16), nullable=False),
        sa.Column('object_id', sa.String(length=64), nullable=False),
        sa.Column('click_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('share_link')
