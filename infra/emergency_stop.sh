#!/bin/bash -e

#####
# emergency_stop.sh
# 緊急停止スクリプト (フェーズ1)
#
# このスクリプトは、JankenHockeyアプリケーションを緊急停止するためのスクリプトです。
# 復旧可能な状態で実行不能にします。
#
# 以下の操作を行います：
# 1. Lambda関数の予約同時実行数を0に設定（実行不能化）
# 2. API Gatewayのスロットリングを0に設定（リクエスト拒否）
#
# 復旧方法：
# - Lambda: aws lambda delete-function-concurrency --function-name <function-name>
# - REST API: ステージ設定でスロットリングを元の値に戻す
# - WebSocket API: ステージ設定でスロットリングを元の値に戻す
#####

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}========================================${NC}"
echo -e "${RED}  JankenHockey 緊急停止スクリプト${NC}"
echo -e "${RED}========================================${NC}"
echo ""

# AWS CLIの確認
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI がインストールされていません${NC}"
    exit 1
fi

# 引数の個数チェック(ちょうど1個)
if [ "$#" -ne 1 ]; then
    echo -e "引数の個数が違います"
    echo -e "Usage: $0 [aws-profile-name]"
    echo ""
    echo "引数:"
    echo "  aws-profile-name   使用するAWS CLIプロファイル名"
    exit 1
fi

# help, --help, h, -h オプションの処理
if [ "$#" -eq 1 ] && [[ "$1" == "help" || "$1" == "--help" || "$1" == "h" || "$1" == "-h" ]]; then
    echo "Usage: $0 [aws-profile-name]"
    echo ""
    echo "引数:"
    echo "  aws-profile-name   使用するAWS CLIプロファイル名"
    exit 0
fi

# AWSプロファイル設定
PROFILE=$1

# リージョン設定（デフォルト: ap-northeast-1）
REGION="${AWS_REGION:-ap-northeast-1}"
echo -e "${YELLOW}リージョン: ${REGION}${NC}"
echo ""

# Lambda関数リスト
LAMBDA_FUNCTIONS=(
    "JankenHockeyAuthorizerFunction"
    "JankenHockeyLoginFunction"
    "JankenHockeyConnectFunction"
    "JankenHockeyDefaultFunction"
    "JankenHockeyDisconnectFunction"
    "JankenHockeyGameTimeoutFunction"
    "JankenHockeyGetRoomsFunction"
    "JankenHockeyCreateRoomFunction"
    "JankenHockeyJoinRoomFunction"
    "JankenHockeySaveCpuBattleHistoryFunction"
    "JankenHockeySaveGuestCpuBattleHistoryFunction"
)

#######################
# Lambda関数の停止
#######################
# 確認プロンプトを入れる
echo -n "本当にLambda・API Gatewayを停止しますか？ (y/N): "
read -r CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]];
then
    echo "操作がキャンセルされました。"
    exit 0
fi

echo -e "${YELLOW}[1/3] Lambda関数の予約同時実行数を0に設定中...${NC}"
echo ""

for func in "${LAMBDA_FUNCTIONS[@]}"; do
    echo -n "  $func ... "
    if aws lambda put-function-concurrency \
        --function-name "$func" \
        --reserved-concurrent-executions 0 \
        --region "$REGION" \
        --profile "$PROFILE" > /dev/null 2>&1; then
        echo -e "${GREEN}完了${NC}"
    else
        echo -e "${RED}失敗（関数が存在しないか、権限がありません）${NC}"
    fi
done
echo ""

#######################
# REST API スロットリング設定
#######################
echo -e "${YELLOW}[2/3] REST API のスロットリングを0に設定中...${NC}"
echo ""

# REST API IDを取得
REST_API_ID=$(aws apigateway get-rest-apis \
    --region "$REGION" \
    --query "items[?name=='JankenHockeyRestAPI'].id" \
    --output text \
    --profile "$PROFILE"  2>/dev/null)

if [ -n "$REST_API_ID" ] && [ "$REST_API_ID" != "None" ]; then
    echo "  REST API ID: $REST_API_ID"
    echo -n "  スロットリング設定中 ... "

    if aws apigateway update-stage \
        --rest-api-id "$REST_API_ID" \
        --stage-name "apiprod" \
        --patch-operations \
            "op=replace,path=/*/*/throttling/rateLimit,value=0" \
            "op=replace,path=/*/*/throttling/burstLimit,value=0" \
        --region "$REGION" \
        --profile "$PROFILE" > /dev/null 2>&1; then
        echo -e "${GREEN}完了${NC}"
    else
        echo -e "${RED}失敗${NC}"
    fi
else
    echo -e "${RED}  REST API が見つかりません${NC}"
fi
echo ""

#######################
# WebSocket API スロットリング設定
#######################
echo -e "${YELLOW}[3/3] WebSocket API のスロットリングを0に設定中...${NC}"
echo ""

# WebSocket API IDを取得
WEBSOCKET_API_ID=$(aws apigatewayv2 get-apis \
    --region "$REGION" \
    --query "Items[?Name=='JankenHockeyAPI'].ApiId" \
    --output text \
    --profile "$PROFILE" 2>/dev/null)

if [ -n "$WEBSOCKET_API_ID" ] && [ "$WEBSOCKET_API_ID" != "None" ]; then
    echo "  WebSocket API ID: $WEBSOCKET_API_ID"
    echo -n "  スロットリング設定中 ... "

    if aws apigatewayv2 update-stage \
        --api-id "$WEBSOCKET_API_ID" \
        --stage-name "prod" \
        --default-route-settings "ThrottlingRateLimit=0,ThrottlingBurstLimit=0" \
        --region "$REGION" \
        --profile "$PROFILE" > /dev/null 2>&1; then
        echo -e "${GREEN}完了${NC}"
    else
        echo -e "${RED}失敗${NC}"
    fi
else
    echo -e "${RED}  WebSocket API が見つかりません${NC}"
fi
echo ""

#######################
# 完了メッセージ
#######################
echo -e "${RED}========================================${NC}"
echo -e "${RED}  緊急停止処理が完了しました${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${YELLOW}復旧方法:${NC}"
echo "  Lambda関数:"
echo "    aws lambda delete-function-concurrency --function-name <function-name> --region $REGION --profile $PROFILE"
echo ""
echo "  REST API:"
if [ -n "$REST_API_ID" ] && [ "$REST_API_ID" != "None" ]; then
    echo "    aws apigateway update-stage --rest-api-id $REST_API_ID --stage-name apiprod \\"
    echo "      --patch-operations 'op=replace,path=/*/*/throttling/rateLimit,value=100' \\"
    echo "                         'op=replace,path=/*/*/throttling/burstLimit,value=200' --region $REGION --profile $PROFILE"
else
    echo "    (REST API IDが取得できませんでした。手動で確認してください)"
fi
echo ""
echo "  WebSocket API:"
if [ -n "$WEBSOCKET_API_ID" ] && [ "$WEBSOCKET_API_ID" != "None" ]; then
    echo "    aws apigatewayv2 update-stage --api-id $WEBSOCKET_API_ID --stage-name prod \\"
    echo "      --default-route-settings 'ThrottlingRateLimit=100,ThrottlingBurstLimit=500' --region $REGION --profile $PROFILE"
else
    echo "    (WebSocket API IDが取得できませんでした。手動で確認してください)"
fi
echo ""
