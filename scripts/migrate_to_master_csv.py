#!/usr/bin/env python3
"""
Migration script to convert individual category CSV files to master CSV format
"""

import os
import pandas as pd
import glob

def migrate_to_master_csv():
    """Convert existing individual category CSV files to master CSV format"""
    
    print("🔄 Migrating individual CSV files to master CSV format...")
    
    # Find all existing category CSV files
    csv_pattern = "csv_outputs/posthog_event_*.csv"
    csv_files = glob.glob(csv_pattern)
    
    if not csv_files:
        print("❌ No individual CSV files found to migrate")
        return False
    
    print(f"✅ Found {len(csv_files)} individual CSV files to migrate")
    
    # Process each file and collect all data
    all_data = {}
    timestamp = None
    
    for csv_file in csv_files:
        print(f"📖 Reading: {csv_file}")
        
        try:
            df = pd.read_csv(csv_file)
            if len(df) > 0:
                # Get timestamp from first file
                if timestamp is None:
                    timestamp = df['timestamp'].iloc[0]
                
                # Get all columns except timestamp
                for col in df.columns:
                    if col != 'timestamp':
                        value = df[col].iloc[0]
                        all_data[col] = value
                        
        except Exception as e:
            print(f"⚠️ Error reading {csv_file}: {e}")
            continue
    
    if not all_data:
        print("❌ No data found in CSV files")
        return False
    
    # Create master CSV
    master_csv_file = "csv_outputs/motor_data_master.csv"
    
    # Prepare the row data
    row_data = {"timestamp": timestamp}
    row_data.update(all_data)
    
    # Create DataFrame and save
    master_df = pd.DataFrame([row_data])
    master_df.to_csv(master_csv_file, index=False)
    
    print(f"✅ Created master CSV: {master_csv_file}")
    print(f"📊 Master CSV contains {len(all_data)} properties from timestamp: {timestamp}")
    
    # Backup the individual files by renaming them
    backup_dir = "csv_outputs/backup_individual_files"
    os.makedirs(backup_dir, exist_ok=True)
    
    for csv_file in csv_files:
        backup_file = os.path.join(backup_dir, os.path.basename(csv_file))
        try:
            os.rename(csv_file, backup_file)
            print(f"📁 Backed up: {os.path.basename(csv_file)} → backup_individual_files/")
        except Exception as e:
            print(f"⚠️ Could not backup {csv_file}: {e}")
    
    print(f"\n🎉 Migration complete! Master CSV created with {len(all_data)} properties")
    print(f"📁 Original files backed up to: {backup_dir}")
    
    return True

if __name__ == "__main__":
    migrate_to_master_csv() 