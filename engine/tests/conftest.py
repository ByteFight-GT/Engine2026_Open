import sys
import os

def pytest_configure():
    # Add a directory to sys.path before tests run
    new_directory = os.path.join(os.getcwd(), "engine", "src")
    if new_directory not in sys.path:
        sys.path.insert(0, new_directory)