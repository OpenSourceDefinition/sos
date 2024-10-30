#!/bin/bash

# Exit on error
set -e

# Check for required environment variables
if [ -z "$GITHUB_TOKEN" ] || [ -z "$GITHUB_REPO" ] || [ -z "$REVOCATION_SECRET" ]; then
    echo "Error: Required environment variables not set"
    echo "Please set: GITHUB_TOKEN, GITHUB_REPO, REVOCATION_SECRET"
    exit 1
fi

# Create lambda layer directory
mkdir -p lambda-layer/python
pip install -r requirements.txt -t lambda-layer/python

# Create lambda directory and copy files
mkdir -p lambda
cp process_signatures.py lambda/
cp revoke_signature.py lambda/
cp config.yml lambda/
mkdir -p lambda/templates
cp templates/* lambda/templates/

# Deploy using CDK
cdk deploy
