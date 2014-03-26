"""video_instance_queue

Revision ID: 22ea09f8a62b
Revises: 956b58937c8
Create Date: 2014-03-25 21:06:27.050634

"""

# revision identifiers, used by Alembic.
revision = '22ea09f8a62b'
down_revision = '956b58937c8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'video_instance_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date_scheduled', sa.DateTime(), nullable=False),
        sa.Column('source_instance', sa.CHAR(length=24), nullable=False),
        sa.Column('target_channel', sa.CHAR(length=24), nullable=False),
        sa.Column('new_instance', sa.CHAR(length=24), nullable=True),
        sa.ForeignKeyConstraint(['new_instance'], ['video_instance.id'], ),
        sa.ForeignKeyConstraint(['source_instance'], ['video_instance.id'], ),
        sa.ForeignKeyConstraint(['target_channel'], ['channel.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('video_instance_queue')
