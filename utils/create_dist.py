import zipfile


import os
import shutil
import zipfile

def copy_to(files_dict, dest_folder):
    """
    Copies specified files into a folder and zips them up.
    
    :param files_to_copy: List of file paths to copy.
    :param dest_folder: Path to the folder where files will be copied.
    :param zip_name: Name (or path) of the zip file to create.
    """
    # Create the destination folder if it doesn't exist
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder, exist_ok=True)

    # Copy each file into the destination folder
    for file_path in files_dict:
        end_loc  = files_dict[file_path]
        if os.path.isdir(file_path):
            shutil.copytree(file_path, os.path.join(dest_folder, end_loc), dirs_exist_ok=True)
            print(f"Copied: {file_path}")
        elif os.path.isfile(file_path):
            shutil.copy(file_path, os.path.join(dest_folder, end_loc))
            print(f"Copied: {file_path}")
        else:
            print(f"Skipped (not found): {file_path}")

def remove_pycache(directory):
    """Removes all __pycache__ directories from the given directory."""
    for root, dirs, files in os.walk(directory, topdown=False):
        if '__pycache__' in dirs:
            pycache_dir = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_dir)
            print(f"Removed: {pycache_dir}")

def zip_folder(dest_folder, zip_name):
    # Create the zip file
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dest_folder):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=dest_folder)
                zipf.write(full_path, arcname)
                print(f"Added to zip: {arcname}")

    print(f"\n Created zip archive: {zip_name}")


def remove_existing_files(files):
    """Remove the destination folder and zip file if they exist."""
    if os.path.isdir(files):
        shutil.rmtree(files)
        print(f"Removed existing folder: {files}")

    if os.path.isfile(files):
        os.remove(files)
        print(f"Removed existing file: {files}")


def create_dist(destination_folder, files_dict, zip_output = False, zip_name =None, make_workspace = False):    
    remove_existing_files(destination_folder)
    copy_to(files_dict, destination_folder)

    remove_pycache(destination_folder)

    if zip_name is None:
        zip_dir = os.path.join("dist", os.path.basename(destination_folder)+".zip")
    else:
        zip_dir = os.path.join("dist", zip_name+".zip")

    if(make_workspace):
        ws_dir = os.path.join(destination_folder, "workspace")
        if not os.path.isdir(ws_dir):
            os.makedirs(ws_dir, exist_ok=True)
    
    if(zip_output):
        remove_existing_files(zip_dir)
        zip_folder(destination_folder, zip_dir)

if __name__ == "__main__":
    create_dist(destination_folder = "dist/engine", 
        files_dict={
            "engine/config": "config",
            "engine/game": "game",
            "engine/game_runner": "game_runner",
            "engine/local_server.py": "local_server.py",
            "engine/run_game.py": "run_game.py",
            "engine/run_game_script.py": "run_game_script.py",
            "engine/sample_controller": "workspace/sample_controller",
            "requirements.txt": "requirements.txt"
        },
        zip_output=True,
        zip_name= "client_terminal_version_v0.1.1"
    )

    # copy everything inside dist/dist_client into the /engine folder of 
    create_dist(destination_folder = "dist/dist_client", 
        files_dict={
            "engine/config": "config",
            "engine/game": "game",
            "engine/game_runner": "game_runner",
            "engine/local_server.py": "local_server.py",
        },
        zip_output=True
    )

    create_dist(destination_folder = "dist/dist_player", 
        files_dict={
            "docs": "docs",
            "engine/game": "game",
            "requirements.txt": "requirements.txt",
            "engine/sample_controller": "examples/sample_controller",
        },
        zip_output=True,
        zip_name= "player_files_v0.1.1"
    )
    

