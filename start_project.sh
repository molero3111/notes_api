#!/bin/bash

# Function to handle SIGINT signal
function handle_sigint {
    echo "Stopping servers..."
    # Stop Django server
    kill $(jobs -p) &>/dev/null
    # Stop npm
    pkill -f "npm start" &>/dev/null
    # Deactivate virtual environment
    deactivate &>/dev/null
    echo "Exiting..."
    exit 0
}

# Trap SIGINT signal
trap handle_sigint SIGINT

# Step 1: cd into backend folder
cd backend

# Step 2: Check if the virtual environment exists
if [ ! -d "notes_manager_venv" ]; then
    # Create a virtual environment if it doesn't exist
    echo "Creating virtual env..."
    python3 -m venv notes_manager_venv
    first_run=true
else
    first_run=false
fi

# Step 2.1: Activate virtual environment and install packages
source notes_manager_venv/bin/activate
pip install -r requirements.txt

# Step 3: Run migrations
echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Step 4: Load fixtures if first time execution
if [ "$first_run" == true ]; then
    echo "Loading initial data..."
    python manage.py loaddata fixtures/*
fi

# Step 5: Run Django server in the background and display output
echo "Starting Django server..."
python manage.py runserver 2>&1 &

# Step 6: cd into frontend folder
cd ../frontend

# Step 7: Install node modules
echo "Installing node modules..."
npm install

# Step 8: Run React app in the background and display output
echo "Starting React app..."
npm start 2>&1 &

# Wait for SIGINT signal
wait

