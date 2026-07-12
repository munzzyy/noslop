#!/bin/bash

# ============================================
# Automated Backup Script
# ============================================
# This script creates a compressed backup of a directory
# and removes backups older than the retention period.

# Configuration - adjust these values as needed
SOURCE_DIR="/path/to/your/data"
BACKUP_DIR="/path/to/your/backups"
RETENTION_DAYS=7

# Step 1: Check if the source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "An error occurred: source directory does not exist"
    exit 1
fi

# Step 2: Create the backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Step 3: Generate a timestamp for the backup filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"

# Step 4: Create the compressed backup archive
echo "Creating backup of $SOURCE_DIR..."
tar -czf "$BACKUP_FILE" "$SOURCE_DIR" 2>/dev/null

# Check if the backup was created successfully
if [ $? -eq 0 ]; then
    echo "Backup created successfully: $BACKUP_FILE ✅"
else
    echo "Something went wrong while creating the backup"
    exit 1
fi

# Step 5: Remove old backups beyond the retention period
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Finally, we print a summary of the backup operation
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup complete! Size: $BACKUP_SIZE"
echo "Note: You can schedule this script with cron to run automatically."
