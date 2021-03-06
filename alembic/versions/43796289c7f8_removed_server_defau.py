"""Removed server default for new date columns

Revision ID: 43796289c7f8
Revises: b5e975c62e5
Create Date: 2013-03-13 11:59:44.250485

"""

# revision identifiers, used by Alembic.
revision = '43796289c7f8'
down_revision = 'b5e975c62e5'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('channel', u'date_updated',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=None,
               existing_nullable=False)
    op.alter_column('channel', u'date_added',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=None,
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_updated',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=None,
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_added',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=None,
               existing_nullable=False)
    op.alter_column('video_locale_meta', u'date_updated',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=None,
               existing_nullable=False)
    op.alter_column('video_locale_meta', u'date_added',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=None,
               existing_nullable=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('video_locale_meta', u'date_added',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=u"2013-03-13 11:51:14.057981+00'::timestamp with time zone",
               existing_nullable=False)
    op.alter_column('video_locale_meta', u'date_updated',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=u"2013-03-13 11:51:14.057981+00'::timestamp with time zone",
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_added',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=u"2013-03-13 11:51:14.057981+00'::timestamp with time zone",
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_updated',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=u"2013-03-13 11:51:14.057981+00'::timestamp with time zone",
               existing_nullable=False)
    op.alter_column('channel', u'date_added',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=u"2013-03-13 11:51:14.057981+00'::timestamp with time zone",
               existing_nullable=False)
    op.alter_column('channel', u'date_updated',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               server_default=u"2013-03-13 11:51:14.057981+00'::timestamp with time zone",
               existing_nullable=False)
    ### end Alembic commands ###
