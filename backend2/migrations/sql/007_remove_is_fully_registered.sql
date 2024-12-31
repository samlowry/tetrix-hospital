-- UP
ALTER TABLE "user" DROP COLUMN is_fully_registered;

-- DOWN
ALTER TABLE "user" ADD COLUMN is_fully_registered BOOLEAN DEFAULT FALSE; 