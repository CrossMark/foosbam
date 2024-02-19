"""previous rating

Revision ID: 3c09c9764288
Revises: acbdc3878208
Create Date: 2024-02-13 20:33:55.510612

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c09c9764288'
down_revision = 'acbdc3878208'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ratings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previous_rating', sa.Integer(), nullable=True))

    with op.batch_alter_table('ratings_att', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previous_rating', sa.Integer(), nullable=True))

    with op.batch_alter_table('ratings_def', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previous_rating', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('ratings_def', schema=None) as batch_op:
        batch_op.drop_column('previous_rating')

    with op.batch_alter_table('ratings_att', schema=None) as batch_op:
        batch_op.drop_column('previous_rating')

    with op.batch_alter_table('ratings', schema=None) as batch_op:
        batch_op.drop_column('previous_rating')

    # ### end Alembic commands ###
