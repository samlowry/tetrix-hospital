-- Drop existing database and user if they exist
DROP DATABASE IF EXISTS tetrix;
DROP USER IF EXISTS tetrix;

-- Create user
CREATE USER tetrix WITH PASSWORD 'tetrixpass';

-- Create database
CREATE DATABASE tetrix WITH OWNER tetrix;

-- Connect to the new database
\c tetrix

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tetrix TO tetrix;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tetrix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tetrix;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";