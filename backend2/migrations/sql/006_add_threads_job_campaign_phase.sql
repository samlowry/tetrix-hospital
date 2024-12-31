-- UP
ALTER TABLE "user" DROP CONSTRAINT check_registration_phase;
ALTER TABLE "user" ADD CONSTRAINT check_registration_phase CHECK (registration_phase IN ('preregistered', 'pending', 'active', 'threads_job_campaign'));

-- DOWN
ALTER TABLE "user" DROP CONSTRAINT check_registration_phase;
ALTER TABLE "user" ADD CONSTRAINT check_registration_phase CHECK (registration_phase IN ('preregistered', 'pending', 'active')); 