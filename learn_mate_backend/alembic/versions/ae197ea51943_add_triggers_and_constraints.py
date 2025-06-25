"""Add triggers and constraints.

Revision ID: ae197ea51943
Revises: 4a6711c4a20d
Create Date: 2025-06-25 11:35:18.887208

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "ae197ea51943"
down_revision: Union[str, Sequence[str], None] = "4a6711c4a20d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add triggers, functions, and constraints from the old SQL migration."""
    # Create function to update message_branches.updated_at
    op.execute(
        text("""
        CREATE OR REPLACE FUNCTION update_message_branches_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
    )

    # Create trigger to update message_branches.updated_at
    op.execute(
        text("""
        CREATE TRIGGER trigger_update_message_branches_updated_at
            BEFORE UPDATE ON message_branches
            FOR EACH ROW
            EXECUTE FUNCTION update_message_branches_updated_at();
        """)
    )

    # Create function to update conversations.updated_at
    op.execute(
        text("""
        CREATE OR REPLACE FUNCTION update_conversations_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """)
    )

    # Create trigger to update conversations.updated_at
    op.execute(
        text("""
        CREATE TRIGGER trigger_update_conversations_updated_at
            BEFORE UPDATE ON conversations
            FOR EACH ROW
            EXECUTE FUNCTION update_conversations_updated_at();
        """)
    )

    # Add check constraint for message version numbers
    op.create_check_constraint("check_version_number_positive", "chat_messages", "version_number > 0")

    # Add check constraint for branch sequence numbers
    op.create_check_constraint("check_sequence_number_positive", "message_branches", "sequence_number > 0")

    # Add default values for timestamp columns if not already present
    op.execute(
        text("""
        ALTER TABLE conversations 
        ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
        ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
        """)
    )

    op.execute(
        text("""
        ALTER TABLE chat_messages 
        ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
        """)
    )

    op.execute(
        text("""
        ALTER TABLE message_branches 
        ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
        ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
        """)
    )

    # Create default branch for any existing conversations without branches
    # This is a data migration that ensures data consistency
    op.execute(
        text("""
        INSERT INTO message_branches (conversation_id, sequence_number, branch_name, created_at, updated_at)
        SELECT DISTINCT c.id, 1, 'Main', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM conversations c
        WHERE NOT EXISTS (
            SELECT 1 FROM message_branches mb WHERE mb.conversation_id = c.id
        );
        """)
    )

    # Update any messages without branch_id to use the default branch
    op.execute(
        text("""
        UPDATE chat_messages cm
        SET branch_id = mb.id
        FROM message_branches mb
        WHERE cm.conversation_id = mb.conversation_id
          AND mb.branch_name = 'Main'
          AND cm.branch_id IS NULL;
        """)
    )


def downgrade() -> None:
    """Remove triggers, functions, and constraints."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_update_message_branches_updated_at ON message_branches")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_conversations_updated_at ON conversations")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_message_branches_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS update_conversations_updated_at()")

    # Drop check constraints
    op.drop_constraint("check_version_number_positive", "chat_messages", type_="check")
    op.drop_constraint("check_sequence_number_positive", "message_branches", type_="check")

    # Remove default values
    op.execute(
        text("""
        ALTER TABLE conversations 
        ALTER COLUMN created_at DROP DEFAULT,
        ALTER COLUMN updated_at DROP DEFAULT;
        """)
    )

    op.execute(
        text("""
        ALTER TABLE chat_messages 
        ALTER COLUMN created_at DROP DEFAULT;
        """)
    )

    op.execute(
        text("""
        ALTER TABLE message_branches 
        ALTER COLUMN created_at DROP DEFAULT,
        ALTER COLUMN updated_at DROP DEFAULT;
        """)
    )
