#!/bin/bash -ex

#####
# deploy.sh
# このスクリプトは、AWS CloudFormationを使ってスタックを作成/更新するためのスクリプトです。
#####
TEMPLATE_FILE="./infra.yaml"

echo "Uploading nested stack templates to S3..."
NESTED_TEMPLATES="authentication-stack.yaml web-hosting-stack.yaml monitoring-stack.yaml websocket-api-stack.yaml rest-api-stack.yaml"
for template in $NESTED_TEMPLATES; do
    if [ -f "$template" ]; then
        echo "Uploading $template to s3://$LAMBDA_BUCKET/$template"
        aws s3 cp "$template" "s3://$LAMBDA_BUCKET/$template"
        echo "$template uploaded successfully."
    else
        echo "Warning: $template not found, skipping..."
    fi
done

# 文法チェック
if ! aws cloudformation validate-template --template-body "file://$TEMPLATE_FILE"; then
    echo 'Failed to validate the template'
    echo 'Aborting...'
    exit 1
fi

# zipファイル名を取得
if [ -z "$LAMBDA_ZIP_PREFIX" ]; then
    echo 'Error: LAMBDA_ZIP_PREFIX environment variable is not set'
    exit 1
fi
LAMBDA_ZIP_FILE=$(find . -maxdepth 1 -name "*$LAMBDA_ZIP_PREFIX*" -type f | tail -n 1 | xargs basename)
if [ -z "$LAMBDA_ZIP_FILE" ]; then
    echo 'Lambda zip file not found'
    echo 'Aborting...'
    exit 1
fi

# CloudFormationをデプロイ
if [ -z "$STACK_NAME" ]; then
    echo 'Error: STACK_NAME environment variable is not set'
    exit 1
fi
if [ -z "$LAMBDA_BUCKET" ]; then
    echo 'Error: LAMBDA_BUCKET environment variable is not set'
    exit 1
fi

# S3バケットと Lambda zipファイルの存在確認
echo "Verifying Lambda zip file exists in S3: s3://$LAMBDA_BUCKET/$LAMBDA_ZIP_FILE"
if ! aws s3 ls "s3://$LAMBDA_BUCKET/$LAMBDA_ZIP_FILE" > /dev/null 2>&1; then
    echo "Error: Lambda zip file '$LAMBDA_ZIP_FILE' not found in S3 bucket '$LAMBDA_BUCKET'"
    echo "Please run './package_lambda.sh' first to upload the Lambda deployment package"
    exit 1
fi
echo "Lambda zip file verified in S3"
set +x
aws cloudformation deploy \
--template-file "$TEMPLATE_FILE" \
--stack-name "$STACK_NAME" \
--capabilities CAPABILITY_NAMED_IAM \
--s3-bucket "$LAMBDA_BUCKET" \
--parameter-overrides LambdaBucket="$LAMBDA_BUCKET" LambdaZipFile="$LAMBDA_ZIP_FILE" OperatorMailAddress="$OPERATOR_MAIL_ADDRESS" \

echo 'Deploy complete'

