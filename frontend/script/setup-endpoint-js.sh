#!/usr/bin/env bash
# 簡易生成スクリプト
# usage: ./setup-endpoint-js.sh <ParentStackName>
set -euo pipefail

PARENT_STACK=$1
REGION="ap-northeast-1"
IN_FILE=../src/api/endpoints.template
OUT_FILE=../src/api/endpoints.js

websocket_api_stack_name=$(
    aws cloudformation describe-stacks --stack-name "${PARENT_STACK}" \
    --region "${REGION}" --query 'Stacks[0].Outputs[?OutputKey==`WebSocketAPIStackName`].OutputValue' \
    --output text | cut -d "/" -f 2
)
ws_api_id=$(
    aws cloudformation describe-stacks --stack-name "${websocket_api_stack_name}" \
    --region ap-northeast-1 --query 'Stacks[0].Outputs[?OutputKey==`JankenHockeyWebSocketAPIId`].OutputValue' \
    --output text
)

mkdir -p "$(dirname "$OUT_FILE")"

sed -e "s|%WS_API_ID%|${ws_api_id}|g" "$IN_FILE" > "$OUT_FILE"

echo "Generated $OUT_FILE"
chmod 644 "$OUT_FILE"
