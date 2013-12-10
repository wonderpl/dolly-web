"""video_instance_comment

Revision ID: 4bc3d359669d
Revises: 55b18a75feba
Create Date: 2013-12-10 16:29:49.621184

"""

# revision identifiers, used by Alembic.
revision = '4bc3d359669d'
down_revision = '55b18a75feba'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'video_instance_comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_instance', sa.CHAR(length=24), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('comment', sa.String(length=120), server_default='', nullable=False),
        sa.Column('date_added', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user'], ['user.id'], ),
        sa.ForeignKeyConstraint(['video_instance'], ['video_instance.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('video_instance_comment_video_instance_idx', 'video_instance_comment', ['video_instance'])
    op.create_index('video_instance_comment_user_idx', 'video_instance_comment', ['user'])
    op.create_index('video_instance_comment_date_added_idx', 'video_instance_comment', ['date_added'])


def downgrade():
    op.drop_table('video_instance_comment')
