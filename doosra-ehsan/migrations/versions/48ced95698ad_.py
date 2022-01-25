"""empty message

Revision ID: 48ced95698ad
Revises: c04ee08449fd
Create Date: 2020-01-20 13:25:22.804479

"""

# revision identifiers, used by Alembic.
revision = '48ced95698ad'
down_revision = 'c04ee08449fd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('uix_ibm_floating_ip_name_region_cloud_id', 'ibm_floating_ips', ['name', 'region', 'cloud_id'])
    op.drop_index('uix_ibm_floating_ip_name_cloud_id', table_name='ibm_floating_ips')
    op.create_unique_constraint('uix_ibm_ike_policy_name_region_cloud_id', 'ibm_ike_policy', ['name', 'region', 'cloud_id'])
    op.drop_index('uix_ibm_ike_policy_name_cloud_id', table_name='ibm_ike_policy')
    op.create_unique_constraint('uix_ibm_image_name_region_visibility_cloud_id', 'ibm_images', ['name', 'cloud_id', 'region', 'visibility'])
    op.drop_index('uix_ibm_image_name_visibility_cloud_id', table_name='ibm_images')
    op.create_unique_constraint('uix_ibm_ipsec_policy_name_region_cloud_id', 'ibm_ipsec_policy', ['name', 'region', 'cloud_id'])
    op.drop_index('uix_ibm_ipsec_policy_name_cloud_id', table_name='ibm_ipsec_policy')
    op.add_column('ibm_subnets', sa.Column('cloud_id', sa.String(length=32), nullable=True))
    op.create_unique_constraint('uix_ibm_subnet_name_cloud_id_vpc_id', 'ibm_subnets', ['name', 'cloud_id', 'vpc_id'])
    op.drop_index('uix_ibm_subnet_name_vpc_id', table_name='ibm_subnets')
    op.create_foreign_key("uix_ibm_subnet_cloud_id", 'ibm_subnets', 'ibm_clouds', ['cloud_id'], ['id'])
    op.create_unique_constraint('uix_ibm_volume_name_resource_id_instance_id_type', 'ibm_volume_attachments', ['name', 'resource_id', 'instance_id', 'type'])
    op.drop_index('uix_ibm_volume_name_instance_id', table_name='ibm_volume_attachments')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('uix_ibm_volume_name_instance_id', 'ibm_volume_attachments', ['name', 'resource_id', 'instance_id'], unique=True)
    op.drop_constraint('uix_ibm_volume_name_resource_id_instance_id_type', 'ibm_volume_attachments', type_='unique')
    op.drop_constraint("uix_ibm_subnet_cloud_id", 'ibm_subnets', type_='foreignkey')
    op.create_index('uix_ibm_subnet_name_vpc_id', 'ibm_subnets', ['name', 'vpc_id'], unique=True)
    op.drop_constraint('uix_ibm_subnet_name_cloud_id_vpc_id', 'ibm_subnets', type_='unique')
    op.drop_column('ibm_subnets', 'cloud_id')
    op.create_index('uix_ibm_ipsec_policy_name_cloud_id', 'ibm_ipsec_policy', ['name', 'region', 'cloud_id'], unique=True)
    op.drop_constraint('uix_ibm_ipsec_policy_name_region_cloud_id', 'ibm_ipsec_policy', type_='unique')
    op.create_index('uix_ibm_image_name_visibility_cloud_id', 'ibm_images', ['name', 'cloud_id', 'region', 'visibility'], unique=True)
    op.drop_constraint('uix_ibm_image_name_region_visibility_cloud_id', 'ibm_images', type_='unique')
    op.create_index('uix_ibm_ike_policy_name_cloud_id', 'ibm_ike_policy', ['name', 'region', 'cloud_id'], unique=True)
    op.drop_constraint('uix_ibm_ike_policy_name_region_cloud_id', 'ibm_ike_policy', type_='unique')
    op.create_index('uix_ibm_floating_ip_name_cloud_id', 'ibm_floating_ips', ['name', 'region', 'cloud_id'], unique=True)
    op.drop_constraint('uix_ibm_floating_ip_name_region_cloud_id', 'ibm_floating_ips', type_='unique')
    # ### end Alembic commands ###