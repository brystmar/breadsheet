#!/bin/bash
# Deploy the breadsheet backend to GCP App Engine as a new version, without sending it traffic.
# Prerequisites: gcloud CLI installed and authenticated (`gcloud init`)
#
# Usage: ./deploy.sh [version]   (defaults to a timestamp, e.g. 20261103t153000)
#
# The deploy process (see CLAUDE.md):
#   1. Run any new Alembic migrations against production first; the current version must keep
#      working with the new schema (expand-then-contract)
#   2. Deploy with this script, which never promotes
#   3. Smoke-test the new version at its own URL
#   4. Move traffic to it; roll back by moving traffic back to the previous version
set -e

# Ensure gcloud uses the system Python, not any active virtualenv
export CLOUDSDK_PYTHON=$(which python3)

VERSION=${1:-$(date -u +%Y%m%dt%H%M%S)}

echo "Deploying breadsheet backend to GCP App Engine as version ${VERSION} (no traffic)..."
gcloud app deploy --quiet --no-promote --version "${VERSION}"

echo ""
echo "Deployed without traffic. Smoke-test it:"
echo "  https://${VERSION}-dot-breadsheet.wl.r.appspot.com/api/v1/recipes"
echo "Then send it all traffic:"
echo "  gcloud app services set-traffic default --splits ${VERSION}=1"
