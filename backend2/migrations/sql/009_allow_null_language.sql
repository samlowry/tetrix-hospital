-- UP
ALTER TABLE "user" ALTER COLUMN language DROP NOT NULL;
ALTER TABLE "user" ALTER COLUMN language DROP DEFAULT;
ALTER TABLE "user" ADD CONSTRAINT check_language_code CHECK (language IS NULL OR language ~ '^[a-z]{2}$');

-- DOWN
ALTER TABLE "user" DROP CONSTRAINT check_language_code;
ALTER TABLE "user" ALTER COLUMN language SET NOT NULL;
ALTER TABLE "user" ALTER COLUMN language SET DEFAULT 'ru'; 