"""user notifications

Revision ID: 2d949040fe49
Revises: 2d2011626632
Create Date: 2013-04-29 13:25:03.220217

"""

# revision identifiers, used by Alembic.
revision = '2d949040fe49'
down_revision = '2d2011626632'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('job_control',
        sa.Column('job', sa.String(length=32), nullable=False),
        sa.Column('last_run', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('job')
    )
    op.get_bind().execute(sa.text(
        "insert into job_control values ('update_user_notifications', '1970-01-01')"
    ))

    op.create_table('user_notification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user', sa.CHAR(length=22), nullable=False, index=True),
        sa.Column('date_created', sa.DateTime(), nullable=False, index=True),
        sa.Column('date_read', sa.DateTime(), nullable=True, index=True),
        sa.Column('message_type', sa.String(16), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('user_activity_actioned', 'user_activity', ['date_actioned'])


def downgrade():
    op.drop_table('user_notification')
    op.drop_table('job_control')
    op.drop_index('user_activity_actioned')
