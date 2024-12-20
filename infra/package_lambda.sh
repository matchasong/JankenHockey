#!/bin/bash -ex

#####
# package_lambda.sh
# このスクリプトは、Lambda関数のデプロイパッケージを作成し、S3にアップロードするためのスクリプトです。
#####

# すでにファイルがある場合は削除
LAMBDA_ZIP_FILE_BEFORE=$(ls -1 | grep $LAMBDA_ZIP_PREFIX | tail -n 1)
if [ $LAMBDA_ZIP_FILE_BEFORE ]; then
    echo 'Lambda zip file found'
    echo 'Removing...'
    rm $LAMBDA_ZIP_FILE_BEFORE
fi

TIMESTAMP=$(date "+%Y%m%d%H%M%S")
LAMBDA_ZIP_FILE=${LAMBDA_ZIP_PREFIX}_${TIMESTAMP}.zip

# デプロイパッケージを作成
# 依存パッケージのインストール
cd lambda
rm -rf package
mkdir package

line = $(cat requirements.txt | wc -l)
if [ $line -eq 0 ]; then
    echo 'No dependencies'
else
   pip install --target ./package -r requirements.txt
fi

# 依存パッケージをzip化
cd package
zip -r ../$LAMBDA_ZIP_FILE .

# Lambda関数のコードをzip化
cd ..
zip $LAMBDA_ZIP_FILE *.py
mv $LAMBDA_ZIP_FILE ../
cd ../

# S3にアップロード
aws s3 cp $LAMBDA_ZIP_FILE s3://$LAMBDA_BUCKET/$LAMBDA_ZIP_FILE