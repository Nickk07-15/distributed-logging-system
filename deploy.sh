#!/bin/bash

# setup
services=(
  "dls-agent-log-producer"
  "dls-elasticsearch-proxy"
  "dls-flink-log-consumer"
  "dls-kafka-broker"
  "dls-log-monitoring-dashboard"
)
environments=("production" "staging" "dev")

if [ -z $1 ]
then
  PS3="Select your service: "
  select image_name in "${services[@]}"
  do if true; then break; fi; done

  PS3="Select your environment: "
  select env in "${environments[@]}"
  do if true; then break; fi; done

else
  container_name=$1
  echo "Error: This script does not accept arguments"
  exit 1
fi

# set variables
container_name="$image_name-$env-container"

# Export Variables
export IMAGE_NAME="$image_name"
export CONTAINER_NAME="$container_name"

# Deploy the container using docker compose
cd deploy || exit

# Remove orphan container and volumes on down
docker compose -f "$image_name"-docker-compose.yml down --volumes --remove-orphans

# Wait for a few seconds to ensure the container is fully stopped and removed
sleep 5

# Prune unused images after rebuild
docker image prune -f

# Wait for a few seconds to ensure the images are pruned
sleep 5

# build without cache
docker compose -f "$image_name"-docker-compose.yml build --no-cache
docker compose -f "$image_name"-docker-compose.yml up -d

# Check if the container is running
if [ "$(docker ps -q -f name="$container_name")" ]; then
    echo "Container $container_name is running."
else
    echo "Container $container_name failed to start."
    exit 1
fi

# Back to root directory
cd .. || exit