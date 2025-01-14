"""changing column name for sensor calibration to include probe, it is slope and intercept, so you have to see what units make sense...

Revision ID: b283fa450931
Revises: 8a99a374f64c
Create Date: 2024-12-18 06:32:35.418159

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b283fa450931'
down_revision: Union[str, None] = '8a99a374f64c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('sensor_calibration', 'fit_ohms_over_celcius', new_column_name='slope')
    op.alter_column('sensor_calibration', 'fit_ohms_intercept', new_column_name='intercept')

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###

    op.alter_column('sensor_calibration', 'slope', new_column_name='fit_ohms_over_celcius')
    op.alter_column('sensor_calibration', 'intercept', new_column_name='fit_ohms_intercept')
    # ### end Alembic commands ###
