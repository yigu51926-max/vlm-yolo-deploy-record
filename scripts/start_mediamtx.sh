#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="mediamtx"
IMAGE="local/mediamtx:1.18.2"
CONFIG_FILE="/home/qi/va-mediamtx/mediamtx.yml"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "配置文件不存在：$CONFIG_FILE"
    exit 1
fi

if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    echo "MediaMTX 已经运行"
elif docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    docker start "$CONTAINER_NAME"
    echo "MediaMTX 已重新启动"
else
    docker run -d \
        --name "$CONTAINER_NAME" \
        --restart unless-stopped \
        --network host \
        -v "$CONFIG_FILE:/mediamtx.yml:ro" \
        "$IMAGE"
    echo "MediaMTX 已创建并启动"
fi

docker logs --tail 10 "$CONTAINER_NAME"
