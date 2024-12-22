#!/bin/bash

# Directory to store backups (outside of repo)
BACKUP_DIR="/var/backups/postgres"

# Docker container name
CONTAINER_NAME="tetrix-hospital-postgres-1"

# Database credentials
DB_USER="tetrix"
DB_NAME="tetrix"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Create a timestamp
TIMESTAMP=$(date +"%Y%m%d%H%M%S")

# Backup file name
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Perform the backup using Docker exec with proper connection settings
/usr/bin/docker exec "$CONTAINER_NAME" pg_dump -h localhost -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"

# Compress the backup
gzip "$BACKUP_FILE"

# Find and delete backups older than 24 hours
find "$BACKUP_DIR" -type f -name "backup_*.sql.gz" -mmin +1440 -exec rm {} \;

# Log the backup
echo "$(date): Backup completed - $BACKUP_FILE.gz" >> "$BACKUP_DIR/backup.log"