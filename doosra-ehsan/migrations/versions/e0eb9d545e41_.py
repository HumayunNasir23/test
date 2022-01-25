"""empty message

Revision ID: e0eb9d545e41
Revises: 9603699f93e8
Create Date: 2020-02-29 16:25:18.040613

"""

# revision identifiers, used by Alembic.
revision = 'e0eb9d545e41'
down_revision = '9603699f93e8'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('secondary_volume_migration_tasks',
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('status', sa.Enum('IN_PROGRESS', 'FAILED', 'SUCCESS', 'CREATED', 'BACKGROUND'), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('message', mysql.MEDIUMTEXT(), nullable=True),
    sa.Column('volume_attached', sa.Boolean(), nullable=True),
    sa.Column('volume_capacity', sa.Integer(), nullable=True),
    sa.Column('instance_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['instance_id'], ['ibm_instances.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('ibm_volume_attachments', sa.Column('is_migration_enabled', sa.Boolean(), nullable=False))
    op.add_column('ibm_volume_attachments', sa.Column('volume_index', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ibm_volume_attachments', 'volume_index')
    op.drop_column('ibm_volume_attachments', 'is_migration_enabled')
    op.drop_table('secondary_volume_migration_tasks')
    # ### end Alembic commands ###