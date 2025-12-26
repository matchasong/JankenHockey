#!/bin/bash -ex

#####
# package_lambda.sh
# このスクリプトは、Lambda関数のデプロイパッケージを作成し、S3にアップロードするためのスクリプトです。
#####

# すでにファイルがある場合は削除
if [ -z "$LAMBDA_ZIP_PREFIX" ]; then
    echo 'Error: LAMBDA_ZIP_PREFIX environment variable is not set'
    exit 1
fi
LAMBDA_ZIP_FILE_BEFORE=$(find . -maxdepth 1 -name "*$LAMBDA_ZIP_PREFIX*" -type f | tail -n 1)
if [ "$LAMBDA_ZIP_FILE_BEFORE" ]; then
    echo 'Lambda zip file found'
    echo 'Removing...'
    rm "$LAMBDA_ZIP_FILE_BEFORE"
fi

TIMESTAMP=$(date "+%Y%m%d%H%M%S")
LAMBDA_ZIP_FILE=${LAMBDA_ZIP_PREFIX}_${TIMESTAMP}.zip

# デプロイパッケージを作成
# 依存パッケージのインストール
cd lambda
rm -rf package
mkdir package

line=$(wc -l < requirements.txt)
if [ "$line" -eq 0 ]; then
    echo 'No dependencies'
else
   pip install --target ./package -r requirements.txt

   # 依存パッケージをzip化
   cd package
   zip -r "../$LAMBDA_ZIP_FILE" .
   cd ..
fi

# Lambda関数のコードをzip化
zip "$LAMBDA_ZIP_FILE" -- *.py
zip -r "$LAMBDA_ZIP_FILE" repositories    # repositoriesパッケージディレクトリを含める
mv "$LAMBDA_ZIP_FILE" ../
cd ../


# S3にアップロード
if [ -z "$LAMBDA_BUCKET" ]; then
    echo 'Error: LAMBDA_BUCKET environment variable is not set'
    exit 1
fi

# S3バケットの存在確認
echo "Checking if S3 bucket exists: $LAMBDA_BUCKET"
if ! aws s3 ls "s3://$LAMBDA_BUCKET" > /dev/null 2>&1; then
    echo "Error: S3 bucket '$LAMBDA_BUCKET' does not exist or is not accessible"
    echo "Please ensure the bucket exists and you have the necessary permissions"
    exit 1
fi

# S3にファイルをアップロード
echo "Uploading $LAMBDA_ZIP_FILE to s3://$LAMBDA_BUCKET/"
if ! aws s3 cp "$LAMBDA_ZIP_FILE" "s3://$LAMBDA_BUCKET/$LAMBDA_ZIP_FILE"; then
    echo "Error: Failed to upload $LAMBDA_ZIP_FILE to S3 bucket $LAMBDA_BUCKET"
    exit 1
fi

# アップロードされたファイルの確認
echo "Verifying uploaded file exists in S3..."
if ! aws s3 ls "s3://$LAMBDA_BUCKET/$LAMBDA_ZIP_FILE" > /dev/null 2>&1; then
    echo "Error: Uploaded file $LAMBDA_ZIP_FILE not found in S3 bucket $LAMBDA_BUCKET"
    exit 1
fi

echo "Successfully uploaded and verified $LAMBDA_ZIP_FILE in S3"
