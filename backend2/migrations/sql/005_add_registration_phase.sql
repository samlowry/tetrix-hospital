-- UP
ALTER TABLE "user" ADD COLUMN registration_phase VARCHAR(20);
UPDATE "user" SET registration_phase = CASE 
    WHEN is_fully_registered THEN 'active'
    ELSE 'pending'
END;
ALTER TABLE "user" ALTER COLUMN registration_phase SET NOT NULL;
ALTER TABLE "user" ADD CONSTRAINT check_registration_phase CHECK (registration_phase IN ('preregistered', 'pending', 'active'));

-- DOWN
ALTER TABLE "user" DROP COLUMN registration_phase; 