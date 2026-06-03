#!/bin/bash
# NOTE: This script is deprecated. We will instead use virtual environments, and simply have
# competitors point the client to where the virtual environment python executable is.
# This will prevent the confusion of having multiple game distribution instances,
# instead the client can submodule dist/dist_client

DEFAULT_NAME="run_game"

OUTPUT_NAME="${1:-$DEFAULT_NAME}"

# Generate hidden-imports for PyInstaller
HIDDEN=$(awk -F '==' '{print "--hidden-import="$1}' requirements.txt | tr '\n' ' ')

pyinstaller \
    --onefile \
    --name "$OUTPUT_NAME" \
    --collect-submodules engine \
    --add-data "engine/config:engine/config" \
    --distpath dist/executable \
    engine/local_server.py $HIDDEN


