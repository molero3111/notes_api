#!/bin/bash

# Set a default image name (replace with your preferred default)
DEFAULT_IMAGE_NAME="molero3111/app_images:notes.v1"

# Ensure mandatory arguments are provided
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Error: Please provide mandatory arguments: files_to_commit commit_message"
  echo "Optional argument: image_name (defaults to $DEFAULT_IMAGE_NAME)"
  exit 1
fi

# Add files to commit
git add "$1"

# Prompt user for confirmation before committing
read -p "Are you sure you want to commit these files (y/N)? " CONFIRM

if [[ ! $CONFIRM =~ ^([Yy]|[Yy]es)$ ]]; then
  echo "Aborting commit."
  exit 1
fi

# Commit changes
git commit -m "$2"

# Push changes to Git repository (assuming configured remote)
git push

# Use provided image name or default
IMAGE_NAME=${$3:-$DEFAULT_IMAGE_NAME}

# Build Docker image
docker build -t "$IMAGE_NAME" .

# Login to Docker Hub securely (avoid storing credentials in the script)
echo "logging in to Docker Hub using 'docker login'"
docker login

# Push Docker image to Docker Hub
docker push "$IMAGE_NAME"

echo "Successfully built and pushed image: $IMAGE_NAME"
