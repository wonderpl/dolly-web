"""user_content_feed

Revision ID: 1f497db49261
Revises: 2465166e851f
Create Date: 2013-07-24 16:02:08.573949

"""

# revision identifiers, used by Alembic.
revision = '1f497db49261'
down_revision = '2465166e851f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'user_content_feed',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False),
        sa.Column('date_added', sa.DateTime(), nullable=False),
        sa.Column('channel', sa.CHAR(length=24), nullable=False),
        sa.Column('video_instance', sa.CHAR(length=24), nullable=True),
        sa.Column('likes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['channel'], ['channel.id']),
        sa.ForeignKeyConstraint(['user'], ['user.id']),
        sa.ForeignKeyConstraint(['video_instance'], ['video_instance.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.execute("""
        insert into user_content_feed ("user", date_added, channel, video_instance)
        select "user", i.date_added, i.channel, i.id
        from video_instance i
        join subscription s on i.channel = s.channel
        where i.date_added > s.date_created
    """)
    op.create_unique_constraint('user_content_feed_uniq', 'user_content_feed',
                                ['user', 'channel', 'video_instance'])
    op.create_index('user_content_feed_user', 'user_content_feed', ['user'])
    op.create_index('user_content_feed_date_added', 'user_content_feed', ['date_added'])
    op.create_index('user_content_feed_channel', 'user_content_feed', ['channel'])


def downgrade():
    op.drop_table('user_content_feed')
