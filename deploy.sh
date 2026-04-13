#!/bin/bash
# Deploy the breadsheet backend to GCP App Engine.
# Prerequisites: gcloud CLI installed and authenticated (`gcloud init`)
set -e

echo "Deploying breadsheet backend to GCP App Engine..."
gcloud app deploy --quiet
echo "Deploy complete. Live at https://breadsheet.com"
