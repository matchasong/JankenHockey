#!/bin/bash -e

#####
# emergency_delete.sh
# 緊急停止スクリプト（フェーズ2）
# このスクリプトは、AWS CloudFormationの親スタックを削除して完全に停止するためのスクリプトです。
# 警告: このスクリプトを実行すると、すべてのリソースが削除され、復旧不可能になります。
#####

echo "=============================================="
echo "緊急停止スクリプト（フェーズ2）"
echo "Emergency Stop Script (Phase 2)"
echo "=============================================="
echo ""
echo "警告: このスクリプトを実行すると、以下のリソースがすべて削除されます："
echo "Warning: Running this script will delete the following resources:"
echo "  - CloudFront Distribution"
echo "  - S3 Bucket (Web Hosting)"
echo "  - API Gateway (REST API, WebSocket API)"
echo "  - Lambda Functions"
echo "  - DynamoDB Tables"
echo "  - Cognito User Pool"
echo "  - CloudWatch Alarms"
echo "  - SNS Topics"
echo ""
echo "この操作は復旧不可能です。"
echo "This operation is NOT recoverable."
echo ""

# help, --help, h, -h オプションの処理
if [ "$#" -eq 1 ] && [[ "$1" == "help" || "$1" == "--help" || "$1" == "h" || "$1" == "-h" ]]; then
    echo 'Usage: ./emergency_delete.sh [stack-name] [aws-profile-name]'
    echo ""
    echo "引数:"
    echo "  stack-name         削除対象のCloudFormationスタック名"
    echo "  aws-profile-name   使用するAWS CLIプロファイル名"
    exit 0
fi

# 引数チェック
if [ "$#" -ne 2 ]; then
    echo '引数の個数が正しくありません。'
    echo 'Usage: ./emergency_delete.sh [stack-name] [aws-profile-name]'
    echo ""
    echo "引数:"
    echo "  stack-name         削除対象のCloudFormationスタック名"
    echo "  aws-profile-name   使用するAWS CLIプロファイル名"
    exit 1
fi
STACK_NAME=$1
PROFILE=$2

# AWS CLIの確認
if ! command -v aws &> /dev/null; then
    echo -e "Error: AWS CLI がインストールされていません"
    exit 1
fi

echo "削除対象スタック / Target stack: $STACK_NAME"
echo ""

# 確認プロンプト
read -r -p "本当にスタック '$STACK_NAME' を削除しますか？ / Are you sure you want to delete stack '$STACK_NAME'? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "中止しました / Aborted."
    exit 0
fi

# スタックの存在確認
echo "スタックの存在を確認しています... / Checking if stack exists..."
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text --profile "$PROFILE" 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" = "NOT_FOUND" ]; then
    echo "エラー: スタック '$STACK_NAME' が見つかりません / Error: Stack '$STACK_NAME' not found"
    exit 1
fi
if [ "$STACK_STATUS" = "DELETE_IN_PROGRESS" ]; then
    echo "スタック '$STACK_NAME' は既に削除中です / Stack '$STACK_NAME' is already being deleted"
    exit 1
fi
echo ""
echo "$STACK_NAME スタックステータス / $STACK_STATUS"

# 最終確認
read -r -p "最終確認: $STACK_NAME を削除して良い場合は 'DELETE' と入力してください / Final confirmation: Type 'DELETE' to proceed: " FINAL_CONFIRM
if [ "$FINAL_CONFIRM" != "DELETE" ]; then
    echo "中止しました / Aborted."
    exit 0
fi

echo ""
echo "スタックを削除しています... / Deleting stack..."

# CloudFormation スタックを削除
aws cloudformation delete-stack --stack-name "$STACK_NAME" --profile "$PROFILE"

echo "スタック削除リクエストを送信しました / Stack deletion request sent."
echo "削除完了を待機しています（最大60分）... / Waiting for stack deletion to complete (max 60 minutes)..."

# スタック削除完了を待機（タイムアウト付き）
TIMEOUT=3600
START_TIME=$(date +%s)
while true; do
    # スタックの現在のステータスを取得
    DESCRIBE_OUTPUT=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --profile "$PROFILE" 2>&1) || true

    # スタックが存在しない場合（削除完了）
    if echo "$DESCRIBE_OUTPUT" | grep -q "does not exist"; then
        break
    fi

    # エラーが発生した場合（ネットワーク問題など）
    if echo "$DESCRIBE_OUTPUT" | grep -q "error\|Error\|Unable to locate"; then
        echo ""
        echo "エラー: AWS CLIでエラーが発生しました / Error: AWS CLI error occurred"
        echo "$DESCRIBE_OUTPUT"
        exit 1
    fi

    CURRENT_STATUS=$(echo "$DESCRIBE_OUTPUT" | grep -o '"StackStatus": "[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -z "$CURRENT_STATUS" ]; then
        # ステータスが取得できない場合は再試行
        sleep 10
        continue
    fi

    if [ "$CURRENT_STATUS" = "DELETE_FAILED" ]; then
        echo ""
        echo "エラー: スタック削除に失敗しました / Error: Stack deletion failed"
        echo "AWSコンソールで詳細を確認してください / Please check AWS Console for details"
        exit 1
    fi

    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo ""
        echo "エラー: タイムアウトしました（60分経過） / Error: Timeout (60 minutes elapsed)"
        echo "スタックは引き続き削除中の可能性があります / Stack may still be deleting"
        exit 1
    fi

    echo "削除中... ($((ELAPSED / 60))分経過) / Deleting... ($((ELAPSED / 60)) minutes elapsed)"
    sleep 30
done

echo ""
echo "=============================================="
echo "スタック '$STACK_NAME' の削除が完了しました"
echo "Stack '$STACK_NAME' has been deleted successfully"
echo "=============================================="
