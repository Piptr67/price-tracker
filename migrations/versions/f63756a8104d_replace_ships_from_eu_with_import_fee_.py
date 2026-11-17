"""replace ships_from_eu with import_fee_due

Revision ID: f63756a8104d
Revises: 65c3a90cdd6d
Create Date: 2026-11-17 21:32:33.836685

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f63756a8104d"
down_revision: Union[str, Sequence[str], None] = "65c3a90cdd6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("price_history", "ships_from_eu", new_column_name="import_fee_due")
    op.execute("UPDATE price_history SET import_fee_due = NOT import_fee_due")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE price_history SET import_fee_due = NOT import_fee_due")
    op.alter_column("price_history", "import_fee_due", new_column_name="ships_from_eu")
