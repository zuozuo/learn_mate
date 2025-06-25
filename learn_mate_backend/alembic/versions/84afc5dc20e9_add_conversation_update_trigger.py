"""Add conversation update trigger.

Revision ID: 84afc5dc20e9
Revises: ae197ea51943
Create Date: 2025-06-25 11:37:43.818151

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "84afc5dc20e9"
down_revision: Union[str, Sequence[str], None] = "ae197ea51943"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trigger to update conversation timestamp when new message is added."""
    # Create function to update conversation timestamp on new message
    op.execute(
        text("""
        CREATE OR REPLACE FUNCTION update_conversation_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE conversations 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = NEW.conversation_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
    )

    # Drop existing trigger if it exists and recreate it
    op.execute("DROP TRIGGER IF EXISTS update_conversation_on_new_message ON chat_messages")

    # Create trigger on chat_messages table
    op.execute(
        text("""
        CREATE TRIGGER update_conversation_on_new_message
        AFTER INSERT ON chat_messages
        FOR EACH ROW
        EXECUTE FUNCTION update_conversation_timestamp();
        """)
    )


def downgrade() -> None:
    """Remove conversation update trigger."""
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_conversation_on_new_message ON chat_messages")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_conversation_timestamp()")
