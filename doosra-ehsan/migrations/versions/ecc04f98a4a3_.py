"""empty message

Revision ID: ecc04f98a4a3
Revises: 3758d5c41eab
Create Date: 2020-05-13 21:45:54.217439

"""

# revision identifiers, used by Alembic.
revision = 'ecc04f98a4a3'
down_revision = '3758d5c41eab'

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("alter table ibm_instances_tasks change `status` `status` ENUM('IN_PROGRESS', 'FAILED', 'SUCCESS');")


def downgrade():
    with op.get_context().autocommit_block():
        op.execute("alter table ibm_instances_tasks change `status` `status` ENUM('IN_PROGRESS', 'FAILED');")
