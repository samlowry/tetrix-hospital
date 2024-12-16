#!/bin/bash

echo "Cleaning database tables..."
psql -d tetrix -c "TRUNCATE TABLE \"user\", metrics RESTART IDENTITY CASCADE;"
echo "Database cleaned successfully!" 