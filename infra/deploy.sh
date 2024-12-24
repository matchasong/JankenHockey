#!/bin/bash -ex

#####
# deploy.sh
# このスクリプトは、AWS CloudFormationを使ってスタックを作成/更新するためのスクリプトです。
#####

TEMPLATE_FILE=./infra.yaml

# 文法チェック
cat $TEMPLATE_FILE | xargs -0 aws cloudformation validate-template --template-body
if [ $? -ne 0 ]; then
    echo 'Failed to validate the template'
    echo 'Aborting...'
    exit 1
fi

# zipファイル名を取得
LAMBDA_ZIP_FILE=$(ls -1 | grep $LAMBDA_ZIP_PREFIX | tail -n 1)
if [ -z $LAMBDA_ZIP_FILE ]; then
    echo 'Lambda zip file not found'
    echo 'Aborting...'
    exit 1
fi

# CloudFormationをデプロイ
set +x
aws cloudformation deploy \
--template-file $TEMPLATE_FILE \
--stack-name $STACK_NAME \
--capabilities CAPABILITY_NAMED_IAM \
--parameter-overrides LambdaBucket=$LAMBDA_BUCKET LambdaZipFile=$LAMBDA_ZIP_FILE AwsAccessKey=$AWS_ACCESS_KEY_ID AwsSecretKey=$AWS_SECRET_ACCESS_KEY

echo 'Deploy complete'

