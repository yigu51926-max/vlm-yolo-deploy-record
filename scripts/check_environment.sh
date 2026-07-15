#!/bin/bash

echo "================================="
echo "   VLM-YOLO Deployment Environment"
echo "================================="

echo ""
echo "[1] System Information"
uname -a

echo ""
echo "[2] GPU Information"
nvidia-smi

echo ""
echo "[3] Docker Version"
docker --version

echo ""
echo "[4] Docker Compose Version"
docker compose version

echo ""
echo "[5] Docker Runtime"
docker info | grep -A5 "Runtimes"

echo ""
echo "[6] Running Containers"
docker ps

echo ""
echo "================================="
echo " Environment Check Finished"
echo "================================="
