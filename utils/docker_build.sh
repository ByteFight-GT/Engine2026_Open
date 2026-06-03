#!/bin/bash

# Default image name
IMAGE_NAME="bf_engine_server"

# Check if an argument for the image name is passed
if [ "$1" ]; then
    IMAGE_NAME=$1
fi

# Run docker build with the image name
docker --debug build -t "$IMAGE_NAME" .