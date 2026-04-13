#!/bin/bash
# Deploy the breadsheet backend to GCP App Engine.
# Prerequisites: gcloud CLI installed and authenticated (`gcloud init`)
set -e

# Ensure gcloud uses the system Python, not any active virtualenv
export CLOUDSDK_PYTHON=$(which python3)

echo "Deploying breadsheet backend to GCP App Engine..."
gcloud app deploy --quiet
echo "Deploy complete. Live at https://breadsheet.com"
