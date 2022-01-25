"""empty message

Revision ID: edc46b0cc9ec
Revises: ca8fe78bbb8f
Create Date: 2021-08-05 07:56:05.959233

"""

# revision identifiers, used by Alembic.
revision = 'edc46b0cc9ec'
down_revision = 'ca8fe78bbb8f'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('uix_ibm_dh_group_name_region_cloudid', 'ibm_dedicated_host_groups', ['name', 'region', 'cloud_id'])
    op.create_unique_constraint('uix_ibm_dh_profile_name_region_cloudid', 'ibm_dedicated_host_profiles', ['name', 'region', 'cloud_id'])
    op.create_unique_constraint('uix_ibm_dh_name_region_cloudid', 'ibm_dedicated_hosts', ['name', 'region', 'cloud_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('uix_ibm_dh_name_region_cloudid', 'ibm_dedicated_hosts', type_='unique')
    op.drop_constraint('uix_ibm_dh_profile_name_region_cloudid', 'ibm_dedicated_host_profiles', type_='unique')
    op.drop_constraint('uix_ibm_dh_group_name_region_cloudid', 'ibm_dedicated_host_groups', type_='unique')
    # ### end Alembic commands ###