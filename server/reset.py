import os
import shutil
from pathlib import Path

def reset_data():
    # Get the base directory (where server.py is located)
    base_dir = Path(__file__).parent
    
    # Define paths to data and uploads folders
    data_folder = base_dir / 'data'
    uploads_folder = base_dir.parent / 'uploads'
    
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
        
    print("\nReset complete! The folders will be recreated when you restart the server.")

if __name__ == "__main__":
    # Ask for confirmation before proceeding
    response = input("This will delete all data and uploaded files. Are you sure? (y/N): ")
    
    if response.lower() == 'y':
        reset_data()
    else:
        print("Reset cancelled.") 