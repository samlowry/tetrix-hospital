#!/bin/bash

# Configuration
BACKUP_DIR="/opt/tetrix-hospital/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Create backup directories if they don't exist
mkdir -p ${BACKUP_DIR}/{postgres,redis}

# Backup PostgreSQL
echo "Starting PostgreSQL backup..."
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dumpall -U ${POSTGRES_USER} > ${BACKUP_DIR}/postgres/backup_${TIMESTAMP}.sql
if [ $? -eq 0 ]; then
    echo "PostgreSQL backup completed"
else
    echo "PostgreSQL backup failed"
    exit 1
fi

# Backup Redis
echo "Starting Redis backup..."
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli SAVE
if [ $? -eq 0 ]; then
    docker-compose -f docker-compose.prod.yml cp redis:/data/dump.rdb ${BACKUP_DIR}/redis/backup_${TIMESTAMP}.rdb
    echo "Redis backup completed"
else
    echo "Redis backup failed"
    exit 1
fi

# Rotate old backups
echo "Cleaning old backups..."
find ${BACKUP_DIR}/postgres -mtime +${RETENTION_DAYS} -delete
find ${BACKUP_DIR}/redis -mtime +${RETENTION_DAYS} -delete

echo "Backup completed successfully at ${TIMESTAMP}" 