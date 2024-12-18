#!/bin/bash

# Configuration
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
RETENTION_DAYS=7

# Ensure backup directory exists
mkdir -p $BACKUP_DIR

# Postgres backup
echo "Starting Postgres backup..."
docker exec postgres pg_dump -Fc dbname > $BACKUP_DIR/pg_$DATE.dump
if [ $? -eq 0 ]; then
    echo "Postgres backup completed"
else
    echo "Postgres backup failed"
    exit 1
fi

# Redis backup
echo "Starting Redis backup..."
docker exec redis redis-cli SAVE
if [ $? -eq 0 ]; then
    cp /data/redis/dump.rdb $BACKUP_DIR/redis_$DATE.rdb
    echo "Redis backup completed"
else
    echo "Redis backup failed"
    exit 1
fi

# Rotate old backups
echo "Cleaning old backups..."
find $BACKUP_DIR -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully" 