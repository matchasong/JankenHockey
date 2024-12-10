# janken hockey infra


GitHub Acitionsを利用する場合
1. Secretsに値を設定してください

2. mainブランチにマージすると、デプロイされます


ローカルで実施する場合

1. 変数を.env.infraに定義
  .env.infra.templateをコピーして.env.infraを作成

2. LambdaをZipパッケージして、S3にアップロード
  source .env.infra
  ./package_lambda.sh

3. CloudFormationを実行
  ./deploy.sh


