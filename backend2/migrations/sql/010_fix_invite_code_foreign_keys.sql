-- UP
-- Revert the current foreign key constraints
ALTER TABLE invite_code DROP CONSTRAINT IF EXISTS invite_code_creator_id_fkey;
ALTER TABLE invite_code DROP CONSTRAINT IF EXISTS invite_code_used_by_id_fkey;

-- Add the correct foreign key constraints
ALTER TABLE invite_code 
    ADD CONSTRAINT invite_code_creator_id_fkey 
    FOREIGN KEY (creator_id) 
    REFERENCES "user"(id) ON DELETE CASCADE;

ALTER TABLE invite_code 
    ADD CONSTRAINT invite_code_used_by_id_fkey 
    FOREIGN KEY (used_by_id) 
    REFERENCES "user"(id) ON DELETE SET NULL;

-- DOWN
-- Revert the current foreign key constraints
ALTER TABLE invite_code DROP CONSTRAINT IF EXISTS invite_code_creator_id_fkey;
ALTER TABLE invite_code DROP CONSTRAINT IF EXISTS invite_code_used_by_id_fkey;

-- Add back the original foreign key constraints without ON DELETE rules
ALTER TABLE invite_code 
    ADD CONSTRAINT invite_code_creator_id_fkey 
    FOREIGN KEY (creator_id) 
    REFERENCES "user"(id);

ALTER TABLE invite_code 
    ADD CONSTRAINT invite_code_used_by_id_fkey 
    FOREIGN KEY (used_by_id) 
    REFERENCES "user"(id); 