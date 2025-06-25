-- Migration: Add message branching support
-- Description: Adds support for message editing and branching functionality

-- Create message_branches table
CREATE TABLE IF NOT EXISTS message_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    parent_message_id UUID REFERENCES chat_messages(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    branch_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(conversation_id, parent_message_id, sequence_number)
);

-- Add indexes for message_branches
CREATE INDEX idx_message_branches_conversation ON message_branches(conversation_id);
CREATE INDEX idx_message_branches_parent ON message_branches(parent_message_id);

-- Add branch-related columns to chat_messages
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES message_branches(id) ON DELETE CASCADE;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS version_number INTEGER DEFAULT 1;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS is_current_version BOOLEAN DEFAULT true;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS parent_version_id UUID REFERENCES chat_messages(id);

-- Add indexes for new columns
CREATE INDEX idx_chat_messages_branch_version ON chat_messages(branch_id, version_number);
CREATE INDEX idx_chat_messages_parent_version ON chat_messages(parent_version_id);
CREATE INDEX idx_chat_messages_current_version ON chat_messages(conversation_id, is_current_version) WHERE is_current_version = true;

-- Create trigger to update message_branches.updated_at
CREATE OR REPLACE FUNCTION update_message_branches_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_message_branches_updated_at
    BEFORE UPDATE ON message_branches
    FOR EACH ROW
    EXECUTE FUNCTION update_message_branches_updated_at();

-- Create default branch for existing conversations
INSERT INTO message_branches (conversation_id, sequence_number, branch_name)
SELECT DISTINCT c.id, 1, 'Main'
FROM conversations c
WHERE NOT EXISTS (
    SELECT 1 FROM message_branches mb WHERE mb.conversation_id = c.id
);

-- Update existing messages to reference the default branch
UPDATE chat_messages cm
SET branch_id = mb.id
FROM message_branches mb
WHERE cm.conversation_id = mb.conversation_id
  AND mb.branch_name = 'Main'
  AND cm.branch_id IS NULL;