"""empty message

Revision ID: 2a813854387a
Revises: 17923ffd701a
Create Date: 2020-01-16 05:10:14.435177

"""

# revision identifiers, used by Alembic.
revision = '2a813854387a'
down_revision = '17923ffd701a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('uix_ibm_ssh_name_region_cloud_id', 'ibm_ssh_keys', ['name', 'region', 'cloud_id'])
    op.drop_index('uix_ibm_ssh_name_cloud_id', table_name='ibm_ssh_keys')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('uix_ibm_ssh_name_cloud_id', 'ibm_ssh_keys', ['name', 'cloud_id'], unique=True)
    op.drop_constraint('uix_ibm_ssh_name_region_cloud_id', 'ibm_ssh_keys', type_='unique')
    # ### end Alembic commands ###
