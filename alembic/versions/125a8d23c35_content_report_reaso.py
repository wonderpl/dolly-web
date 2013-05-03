"""content_report reason

Revision ID: 125a8d23c35
Revises: 6e834dba68f
Create Date: 2013-05-03 11:42:00.960408

"""

# revision identifiers, used by Alembic.
revision = '125a8d23c35'
down_revision = '6e834dba68f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('content_report', sa.Column('reason', sa.String(length=256), nullable=False))
    op.drop_constraint('content_report_object_type_object_id_key', 'content_report')
    op.create_unique_constraint('content_report_uniq', 'content_report',
                                ['object_type', 'object_id', 'reason'])


def downgrade():
    op.drop_column('content_report', 'reason')
