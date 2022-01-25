"""empty message

Revision ID: f676210d72f7
Revises: 715341470fef
Create Date: 2020-04-03 17:22:49.905112

"""

# revision identifiers, used by Alembic.
revision = 'f676210d72f7'
down_revision = '715341470fef'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ibm_instances_tasks', sa.Column('in_focus', sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ibm_instances_tasks', 'in_focus')
    # ### end Alembic commands ###