"""Add user authentication tables.

Revision ID: e0c85538e3c1
Revises: 84afc5dc20e9
Create Date: 2025-06-25 15:35:53.103741

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e0c85538e3c1"
down_revision: Union[str, Sequence[str], None] = "84afc5dc20e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to user table
    op.add_column("user", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column("user", sa.Column("is_active", sa.Boolean(), nullable=True))
    op.add_column("user", sa.Column("is_verified", sa.Boolean(), nullable=True))
    op.add_column("user", sa.Column("last_login_at", sa.DateTime(), nullable=True))

    # Update existing rows with default values
    op.execute("UPDATE user SET username = email WHERE username IS NULL")
    op.execute("UPDATE user SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE user SET is_verified = false WHERE is_verified IS NULL")

    # Make username and new columns not nullable
    op.alter_column("user", "username", nullable=False)
    op.alter_column("user", "is_active", nullable=False)
    op.alter_column("user", "is_verified", nullable=False)

    # Create unique index on username
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    # Create login_history table
    op.create_table(
        "loginhistory",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("login_at", sa.DateTime(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loginhistory_user_id", "loginhistory", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop login_history table
    op.drop_index("ix_loginhistory_user_id", table_name="loginhistory")
    op.drop_table("loginhistory")

    # Drop username index
    op.drop_index("ix_user_username", table_name="user")

    # Remove columns from user table
    op.drop_column("user", "last_login_at")
    op.drop_column("user", "is_verified")
    op.drop_column("user", "is_active")
    op.drop_column("user", "username")
