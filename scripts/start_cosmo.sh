#!/bin/bash

set -e

COSMO_DIR=~/cosmo-edge

echo "================================="
echo " Starting CosmoEdge x86"
echo "================================="

if [ ! -d "$COSMO_DIR" ]; then
    echo "ERROR: CosmoEdge directory not found:"
    echo "$COSMO_DIR"
    exit 1
fi

cd "$COSMO_DIR"

docker compose \
    -f docker-compose.x86.yml \
    up -d cosmo-x86

echo ""
echo "CosmoEdge container status:"
docker ps --filter name=cosmo-x86

echo ""
echo "CosmoEdge started."
