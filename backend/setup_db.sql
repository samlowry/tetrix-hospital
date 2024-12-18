-- We don't need to create database/user as they're created by Docker
-- based on POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB environment variables

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges (already owner, but let's ensure full access)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tetrix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tetrix;

-- Create necessary schemas and tables here
-- Example:
-- CREATE TABLE IF NOT EXISTS users (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );