#!/bin/bash
set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Starting Meta Ads API server on http://localhost:5000"
echo "Health check: http://localhost:5000/health"
echo "Fetch data:   http://localhost:5000/fetch-meta-data"
echo ""

python server.py
