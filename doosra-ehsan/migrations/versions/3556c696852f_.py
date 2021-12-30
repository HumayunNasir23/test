"""empty message

Revision ID: 3556c696852f
Revises: 02dd0fd8b33a
Create Date: 2020-02-16 11:37:06.828652

"""

# revision identifiers, used by Alembic.
revision = '3556c696852f'
down_revision = '02dd0fd8b33a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('image_conversion_instances',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('softlayer_id', sa.Integer(), nullable=True),
    sa.Column('username', sa.String(length=1024), nullable=True),
    sa.Column('_password', sa.String(length=1024), nullable=True),
    sa.Column('ip_address', sa.String(length=15), nullable=True),
    sa.Column('datacenter', sa.String(length=1024), nullable=False),
    sa.Column('cpus', sa.Integer(), nullable=False),
    sa.Column('memory', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('CREATE_PENDING', 'CREATING', 'ACTIVE', 'DELETE_PENDING', 'DELETING'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('image_conversion_task_logs',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('image_size', sa.Integer(), nullable=False),
    sa.Column('download_time', sa.Integer(), nullable=False),
    sa.Column('convert_time', sa.Integer(), nullable=False),
    sa.Column('upload_time', sa.Integer(), nullable=False),
    sa.Column('completion_time', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('image_conversion_tasks',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('image_size_mb', sa.Integer(), nullable=False),
    sa.Column('region', sa.String(length=16), nullable=False),
    sa.Column('image_name', sa.String(length=255), nullable=False),
    sa.Column('cos_bucket_name', sa.String(length=255), nullable=False),
    sa.Column('_status', sa.Enum('CREATED', 'RUNNING', 'SUCCESSFUL', 'FAILED'), nullable=False),
    sa.Column('_step', sa.Enum('PENDING_PROCESS_START', 'FILES_UPLOADING', 'IMAGE_DOWNLOADING', 'IMAGE_CONVERTING', 'IMAGE_VALIDATING', 'IMAGE_UPLOADING', 'PENDING_CLEANUP', 'CLEANING_UP', 'PROCESS_COMPLETED'), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('download_started_at', sa.DateTime(), nullable=True),
    sa.Column('conversion_started_at', sa.DateTime(), nullable=True),
    sa.Column('validation_started_at', sa.DateTime(), nullable=True),
    sa.Column('upload_started_at', sa.DateTime(), nullable=True),
    sa.Column('instance_id', sa.String(length=32), nullable=True),
    sa.Column('cloud_id', sa.String(length=32), nullable=False),
    sa.ForeignKeyConstraint(['cloud_id'], ['ibm_clouds.id'], ),
    sa.ForeignKeyConstraint(['instance_id'], ['image_conversion_instances.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('image_conversion_tasks')
    op.drop_table('image_conversion_task_logs')
    op.drop_table('image_conversion_instances')
    # ### end Alembic commands ###