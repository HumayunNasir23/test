"""empty message

Revision ID: 935eae637a37
Revises: 91da72c279f9
Create Date: 2020-06-03 18:48:06.895816

"""

# revision identifiers, used by Alembic.
revision = '935eae637a37'
down_revision = '91da72c279f9'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ibm_tasks', 'result', existing_type=sa.Text(), type_=mysql.LONGTEXT())
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('ibm_tasks', 'result', existing_type=mysql.LONGTEXT(), type_=sa.Text())
    # ### end Alembic commands ###