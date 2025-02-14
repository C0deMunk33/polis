import os
import shutil
from pathlib import Path

def reset_data():
    # Get the base directory (where server.py is located)
    base_dir = Path(__file__).parent
    
    # Define paths to data and uploads folders
    data_folder = base_dir / 'data'
    uploads_folder = base_dir.parent / 'uploads'
    db_file = base_dir / 'forum.db'  # Add database file path
    
    # Delete data folder if it exists
    if data_folder.exists():
        print(f"Deleting data folder at: {data_folder}")
        shutil.rmtree(data_folder)
    else:
        print("Data folder doesn't exist - nothing to delete")
        
    # Delete uploads folder if it exists
    if uploads_folder.exists():
        print(f"Deleting uploads folder at: {uploads_folder}")
        shutil.rmtree(uploads_folder)
    else:
        print("Uploads folder doesn't exist - nothing to delete")

    # Delete database file if it exists
    if db_file.exists():
        print(f"Deleting database file at: {db_file}")
        os.remove(db_file)
    else:
        print("Database file doesn't exist - nothing to delete")
        
    print("\nReset complete! The folders and database will be recreated when you restart the server.")

if __name__ == "__main__":
    # Ask for confirmation before proceeding
    response = input("This will delete all data, uploaded files and the database. Are you sure? (y/N): ")
    
    if response.lower() == 'y':
        reset_data()
    else:
        print("Reset cancelled.") 