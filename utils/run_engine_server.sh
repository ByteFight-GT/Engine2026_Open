#!/bin/bash

# Check if we have the required number of arguments

IMAGE_NAME="bf_engine_server"



if [ "$#" -eq 1 ]; then
    CONTAINER_NAME=$1
    docker rm -f "$CONTAINER_NAME" 
    docker run --name "$CONTAINER_NAME"  --env-file ".env" -d  "$IMAGE_NAME"
    exit 0
fi



if [[ "$#" -gt 4 || "$#" -lt 3 ]]; then
    echo "Usage: $0 <container_name> [<cpuset> <mem>] [<image>]"
    exit 1
fi

CONTAINER_NAME=$1

if [ "$5" ]; then
    IMAGE_NAME=$5
fi
CPUSET=$2
MEM=$3

# Run the Docker container with specified name, cpu limit, and cpuset
#--cpuset-cpus="$CPUSET"

docker rm -f "$CONTAINER_NAME" 
docker run --name "$CONTAINER_NAME"  --cpuset-cpus="$CPUSET" --security-opt no-new-privileges \
    --memory="$MEM" --env-file ".env" -d  --restart unless-stopped "$IMAGE_NAME"
