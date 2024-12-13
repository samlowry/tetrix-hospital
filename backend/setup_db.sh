#!/bin/bash

# Check if PostgreSQL is running
if ! pg_isready; then
    echo "Starting PostgreSQL..."
    brew services start postgresql
    sleep 3  # Wait for PostgreSQL to start
fi

# Run the setup script
echo "Setting up database..."
psql postgres -f db_setup.sql

echo "Database setup complete!" 