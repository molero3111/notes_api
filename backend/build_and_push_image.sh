#!/bin/bash

# Set a default image name (replace with your preferred default)
DEFAULT_IMAGE_NAME="molero3111/app_images:notes.v1"

git status

echo "Pushing git commits..."

# Push changes to Git repository (assuming configured remote)
git push

# Use provided image name or default
IMAGE_NAME=$1

# Check for empty image name
if [ -z "$IMAGE_NAME" ]; then
    echo "No image name provided, using default: $DEFAULT_IMAGE_NAME"
    IMAGE_NAME=$DEFAULT_IMAGE_NAME
fi

echo "Building image: $IMAGE_NAME"

# Build Docker image
docker build -t "$IMAGE_NAME" .

# Login to Docker Hub securely (avoid storing credentials in the script)
echo "logging in to Docker Hub using 'docker login'"
docker login

echo "Pushing image: $IMAGE_NAME"
# Push Docker image to Docker Hub
docker push "$IMAGE_NAME"

echo "Successfully built and pushed image: $IMAGE_NAME"
