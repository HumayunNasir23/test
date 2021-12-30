"""empty message

Revision ID: bc14742ba88a
Revises: 66b9b2c4c99b
Create Date: 2020-04-23 14:16:23.109242

"""

# revision identifiers, used by Alembic.
revision = 'bc14742ba88a'
down_revision = '66b9b2c4c99b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('release_notes',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('release_date', sa.DateTime(), nullable=False),
    sa.Column('url', sa.String(length=255), nullable=True),
    sa.Column('version', sa.String(length=32), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('project_release_notes',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('release_notes_id', sa.String(length=32), nullable=False),
    sa.Column('project_id', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['release_notes_id'], ['release_notes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('project_release_notes')
    op.drop_table('release_notes')
    # ### end Alembic commands ###