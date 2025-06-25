"""Fix loginhistory id column default value.

Revision ID: fix_loginhistory_id
Revises: e0c85538e3c1
Create Date: 2025-06-25 19:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "fix_loginhistory_id"
down_revision: Union[str, Sequence[str], None] = "e0c85538e3c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add default value for loginhistory.id column."""
    # Set default value for id column to use uuid_generate_v4()
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.alter_column(
        "loginhistory",
        "id",
        server_default=sa.text("uuid_generate_v4()"),
        existing_type=postgresql.UUID(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Remove default value for loginhistory.id column."""
    op.alter_column(
        "loginhistory",
        "id",
        server_default=None,
        existing_type=postgresql.UUID(),
        existing_nullable=False,
    )
