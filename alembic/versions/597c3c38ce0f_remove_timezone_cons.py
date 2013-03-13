"""remove timezone constraints from models

Revision ID: 597c3c38ce0f
Revises: 43796289c7f8
Create Date: 2013-03-13 12:53:40.192815

"""

# revision identifiers, used by Alembic.
revision = '597c3c38ce0f'
down_revision = '43796289c7f8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('video', u'date_added',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('video', u'date_updated',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('video_locale_meta', u'date_added',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('video_locale_meta', u'date_updated',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('video_instance', u'date_added',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('channel', u'date_added',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('channel', u'date_updated',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_added',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_updated',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DateTime(),
               existing_nullable=False)
    ### end Alembic commands ###


def downgrade():
    op.alter_column('video', u'date_added',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('video', u'date_updated',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('video_locale_meta', u'date_added',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('video_locale_meta', u'date_updated',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('video_instance', u'date_added',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('channel', u'date_added',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('channel', u'date_updated',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_added',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('channel_locale_meta', u'date_updated',
               existing_type=sa.DateTime(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    ### end Alembic commands ###
