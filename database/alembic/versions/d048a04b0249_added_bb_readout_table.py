"""Added bb readout table

Revision ID: d048a04b0249
Revises: 4f0263597922
Create Date: 2025-04-23 11:10:01.389061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd048a04b0249'
down_revision: Union[str, None] = '4f0263597922'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bb_resistance_path',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('module_id', sa.Integer(), nullable=False),
    sa.Column('module_orientation', sa.String(length=50), nullable=True),
    sa.Column('plate_position', sa.Integer(), nullable=True),
    sa.Column('ref_resistor_value', sa.Float(), nullable=False),
    sa.Column('path_name', sa.String(length=50), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('raw_voltage', sa.String(length=50), nullable=False),
    sa.ForeignKeyConstraint(['module_id'], ['module.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bb_resistance_path_module_id'), 'bb_resistance_path', ['module_id'], unique=False)
    op.create_index(op.f('ix_bb_resistance_path_run_id'), 'bb_resistance_path', ['run_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_bb_resistance_path_run_id'), table_name='bb_resistance_path')
    op.drop_index(op.f('ix_bb_resistance_path_module_id'), table_name='bb_resistance_path')
    op.drop_table('bb_resistance_path')
    # ### end Alembic commands ###
