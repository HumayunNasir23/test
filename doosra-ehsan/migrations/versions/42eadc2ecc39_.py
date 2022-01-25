"""empty message

Revision ID: 42eadc2ecc39
Revises: f1efc4bfca03
Create Date: 2020-12-21 10:38:20.884272

"""

# revision identifiers, used by Alembic.
revision = '42eadc2ecc39'
down_revision = 'f1efc4bfca03'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('ibm_instances', sa.Column('original_operating_system_name', sa.String(length=255), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ibm_instances', 'original_operating_system_name')
    # ### end Alembic commands ###