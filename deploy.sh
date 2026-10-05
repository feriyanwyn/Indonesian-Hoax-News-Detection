#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

IMAGE_NAME="hoax-detection-app"
CONTAINER_NAME="hoax-detection-container"
PORT=8501

echo "=================================================="
echo "🛡️ Starting Indonesian Hoax Classifier Deployment"
echo "=================================================="

# 1. Build the Docker image
echo "Step 1: Building Docker image '${IMAGE_NAME}:latest'..."
docker build -t ${IMAGE_NAME}:latest .

# 2. Stop and remove existing container if it exists
if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    echo "Step 2: Stopping and removing existing container '${CONTAINER_NAME}'..."
    docker stop ${CONTAINER_NAME} || true
    docker rm ${CONTAINER_NAME} || true
else
    echo "Step 2: No existing container named '${CONTAINER_NAME}' found. Skipping removal."
fi

# 3. Run the container
echo "Step 3: Running container '${CONTAINER_NAME}' on port ${PORT}..."
docker run -d \
  --name ${CONTAINER_NAME} \
  -p ${PORT}:${PORT} \
  --restart unless-stopped \
  ${IMAGE_NAME}:latest

# 4. Print status
echo "=================================================="
echo "🎉 Deployment Successful!"
echo "=================================================="
echo "Container Status:"
docker ps -f name=${CONTAINER_NAME}
echo ""
echo "You can access the dashboard at:"
echo "👉 Local: http://localhost:${PORT}"
echo "=================================================="
