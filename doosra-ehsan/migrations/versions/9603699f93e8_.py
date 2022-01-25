"""empty message

Revision ID: 9603699f93e8
Revises: ecfb13bacca1
Create Date: 2020-02-29 15:40:31.025710

"""

# revision identifiers, used by Alembic.
revision = '9603699f93e8'
down_revision = 'ecfb13bacca1'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ibm_instance_profiles', 'family',
               existing_type=mysql.ENUM('BALANCED', 'CPU', 'MEMORY'),
               type_=mysql.ENUM('BALANCED', 'COMPUTE', 'MEMORY', 'GPU'),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ibm_instance_profiles', 'family',
               existing_type=mysql.ENUM('BALANCED', 'CPU', 'MEMORY'),
               type_=mysql.ENUM('BALANCED', 'COMPUTE', 'MEMORY', "GPU"),
               existing_nullable=True)
    # ### end Alembic commands ###