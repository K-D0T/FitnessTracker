import os
import shutil
import sys
from pathlib import Path

def replace_in_file(file_path, old_str, new_str):
    with open(file_path, 'r', encoding='utf-8') as file:
        filedata = file.read()

    filedata = filedata.replace(old_str, new_str)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(filedata)

def rename_project(template_path, new_name):
    old_name = 'fitnesstracker'  # The name of the inner project directory to be replaced
    # Moving the new project directory one level up from the current grandparent directory
    new_project_path = template_path.parent.parent / new_name

    # Copy template project to new location
    shutil.copytree(template_path.parent, new_project_path)  # Copy the entire parent directory

    # Rename the inner project directory
    os.rename(new_project_path / old_name, new_project_path / new_name)

    # Update settings and other Python files
    for file_path in new_project_path.rglob('*.py'):
        replace_in_file(file_path, old_name, new_name)

    # Update any other file types as necessary
    for file_path in new_project_path.rglob('*.*'):
        if file_path.suffix in ['.txt', '.md', '.html', '.json']:  # Extend file types as needed
            replace_in_file(file_path, old_name, new_name)

    print(f"Project {new_name} created successfully at {new_project_path}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python changeprojectname.py 'new_project_name'")
        sys.exit(1)

    new_project_name = sys.argv[1]
    template_project_path = Path(__file__).resolve().parent / 'fitnesstracker'  # Assumes this script is directly in the root of the fitnesstracker
    rename_project(template_project_path, new_project_name)
