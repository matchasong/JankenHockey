# janken hockey infra

# 概要

Janken Hockey のインフラをコードで管理  
CloudFormation テンプレートのサイズ制限（51,200 バイト）を回避するため、ネストされたスタック構造を採用

- IaC

```
infra-oidc.yaml (GitHub Actions用のOIDCプロバイダとロール) GitHub Actionsの前提のためこれだけ別管理。AWSコンソールから手動でデプロイ
infra.yaml (メインスタック)
├── authentication-stack.yaml 認証機能スタック(Cognitoユーザプール, Authorizer Lambda)
├── websocket-api-stack.yaml WebSocket APIスタック(API Gateway, Lambda, DynamoDB)
├── rest-api-stack.yaml APIスタック(API Gateway, Lambda)
├── web-hosting-stack.yaml Webホスティングスタック(S3, CloudFront)
└── monitoring-stack.yaml 監視機能スタック(CloudWatchアラーム、SNSトピック)
```

- ビルド

  - deploy.sh  
    package_lambda.sh を呼び出して Lambda パッケージをビルドして S3 バケットにアップロードする。  
    さらに CloudFormation を利用してインフラを構築(新規構築または更新)、および、Lambda パッケージをを AWS Lambda にデプロイして実行可能な状態にする。
  - package_lambda.sh  
    lambda フォルダを、AWS Lambda にアップロード可能な zip 形式にビルドし、S3 バケットにアップロードする。  
    (deploy.sh から呼び出されるため通常は意識しなくて良い)

- 緊急停止
  - emergency_stop.sh  
    緊急停止スクリプト（フェーズ1）。AWS CLI を使用して Lambda の同時接続数および API Gateway のスロットリングの値を0にして、実行できないようにする。
    
    実行方法
    ```
    emergency_stop.sh [AWSプロファイル名]
    ```

  - emergency_delete.sh  
    緊急停止スクリプト（フェーズ 2）。AWS CLI を使用して CloudFormation 親スタックを削除し、すべてのリソースを完全に削除する。  
    **警告: この操作は復旧不可能です。実行前に必ず確認してください。**

    実行方法

    ```
    ./emergency_delete.sh [スタック名] [AWSプロファイル名]
    ```

- lambda  
  基本的には、1 つの Lambda 関数に対して、1 つの Python ファイルが対応。  
  ただし、DB アクセス部分は repository サブフォルダに別ファイルとしている。

# 前提条件

- AWS CLI v2 がインストールされていること
- AWS CLI でデプロイ先の AWS アカウントにアクセスできること
- AWS CloudFormation が利用できること
- S3 バケットが作成されていること

# Secrets に設定が必要な値(.env.infra.template を参照)

- STACK_NAME: スタック名
- PROFILE: AWS AWS CLI のプロファイル名
- LAMBDA_BUCKET: Lambda の Zip パッケージをアップロードする S3 バケット名
- LAMBDA_ZIP_PREFIX: Lambda の Zip パッケージの S3 オブジェクトキーのプレフィックス
- OPERATOR_MAIL_ADDRESS: 監視メール宛先アドレス

# 構築手順

## 1. OIDC 設定

1. infra-oidc.yaml をデプロイして、OIDC プロバイダとロールを作成する
   - GitHubRepositoryName は、{GitHub のユーザ名}/{リポジトリ名} の形式で指定すること
   - 「CAPABILITY_NAMED_IAM」を指定すること(IAM ロールを作成するため)

## 2. その他リソースの作成

### GitHub Acitions を利用する場合

1. GitHub Actions の Secrets に値を設定（先述の「Secrets に設定が必要な値」欄を参照）

2. main ブランチにマージすると、デプロイされる

### ローカルから aws cli 経由で構築する場合

1. 変数を.env.infra に定義  
   .env.infra.template をコピーして.env.infra を作成

2. Lambda を Zip パッケージして、S3 にアップロード

```
   source .env.infra
   ./package_lambda.sh
```

3. CloudFormation を実行

```
   ./deploy.sh
```

# 緊急停止手順

**警告: この操作は復旧不可能です。すべてのリソースが削除されます。**

緊急時に全リソースを削除する場合は、以下のコマンドを実行します:

```bash
source .env.infra
./emergency_delete.sh
```

スクリプトは以下の処理を実行します:

1. 確認プロンプトを表示（"yes" と "DELETE" の入力が必要）
2. AWS CLI を使用して親スタックを削除
3. スタック削除完了まで待機

# 技術スタック

- AWS

  - AWS CloudFormation
  - AWS Lambda
  - Amazon API Gateway(REST API, WebSocket API)
  - Amazon DynamoDB
  - Amazon Cognito(User Pool)
  - Amazon S3
  - Amazon CloudFront
  - Amazon CloudWatch
  - Amazon SNS

- Language / Framework

  - Python 3.12 (Lambda)

- Infrastructure as Code

  - AWS CloudFormation YAML

- CI/CD
  - [GitHub Actions](https://docs.github.com/ja/actions)  
    ../.github/workflows/deploy_backend.yml に定義
