#!/bin/bash

# Exit on error
set -e

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check for required AWS environment variables
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_DEFAULT_REGION" ]; then
    echo "Error: Required AWS environment variables not set"
    echo "Please set in .env file:"
    echo "  AWS_ACCESS_KEY_ID"
    echo "  AWS_SECRET_ACCESS_KEY"
    echo "  AWS_DEFAULT_REGION"
    exit 1
fi

# Install Node.js dependencies
npm install

# Create lambda layer directory and install dependencies
mkdir -p email/lambda-layer/python
pip install -r requirements.txt -t email/lambda-layer/python

# Create lambda function directory and copy function code
mkdir -p email/lambda
if [ -d "lambda" ]; then
    echo "Copying lambda function code..."
    cp -r lambda/* email/lambda/
fi

# Copy templates and other static assets
if [ -d "lambda/templates" ]; then
    echo "Copying email templates..."
    cp -r lambda/templates email/lambda-layer/python/
fi

export CDK_DOCKER=podman

# Deploy using CDK
npx cdk deploy
