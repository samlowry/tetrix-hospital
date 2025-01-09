-- Add unique constraint to threads_job_campaign table
ALTER TABLE threads_job_campaign ADD CONSTRAINT unique_user_campaign UNIQUE (user_id); 