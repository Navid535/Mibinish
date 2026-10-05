#!/bin/bash
# scripts/backup_db.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL | gzip > /backups/keeply_${TIMESTAMP}.sql.gz
find /backups -name "*.sql.gz" -mtime +30 -delete  # نگه‌داری ۳۰ روز
