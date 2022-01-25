"""empty message

Revision ID: 715341470fef
Revises: 27a9c81d0499
Create Date: 2020-03-29 21:54:35.495590

"""

# revision identifiers, used by Alembic.
revision = '715341470fef'
down_revision = '27a9c81d0499'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('ibm_instances_tasks',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('status', sa.Enum('IN_PROGRESS', 'FAILED', 'SUCCESS'), nullable=False),
    sa.Column('base_task_id', sa.String(length=32), nullable=False),
    sa.Column('ic_task_id', sa.String(length=32), nullable=True),
    sa.Column('softlayer_cloud_id', sa.String(length=32), nullable=True),
    sa.Column('type', sa.Enum('take_snapshot', 'upload_to_cos', 'image_conversion', 'create_custom_image', 'create_instance_subsequent'), nullable=False),
    sa.Column('image_create_date', sa.String(length=32), nullable=True),
    sa.Column('cloud', sa.String(length=32), nullable=False),
    sa.Column('instance_id', sa.String(length=32), nullable=True),
    sa.Column('classical_instance_id', sa.String(length=32), nullable=True),
    sa.ForeignKeyConstraint(['cloud'], ['ibm_clouds.id'], ),
    sa.ForeignKeyConstraint(['instance_id'], ['ibm_instances.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('ibm_instances_tasks')
    # ### end Alembic commands ###