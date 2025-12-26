# デプロイ設計

当プロジェクトにおけるビルドおよびデプロイの方針を記載する

## 要件

当プロジェクトは、Vue.js を用いた SPA クライアントと、AWS を用いたサーバーレスバックエンドで構成されている。
これらのリソースを効率的にビルド・デプロイするため、下記を要件とした。

- バックエンドの自動デプロイ

  - バックエンドについて、main ブランチにマージされた際に、自動的にデプロイを実行する

- フロントエンドの自動デプロイ

  - フロントエンドについて、main ブランチにマージされた際に、自動的にデプロイを実行する
  - フロントエンドは CloudFront 経由で配信するため、更新デプロイ時には CloudFront のキャッシュを削除する

- なお、いずれの自動デプロイ機能も、matchasong/JankenHockey リポジトリ(公開用リポジトリ)では無効としている。

## 採用技術

- GitHub Actions
  自動デプロイのツールとして [GitHub Actions](https://docs.github.com/ja/actions) を採用した。  
  当プロジェクトは GitHub でソースコードを管理しているため、GitHub Actions を利用することでシームレスに CICD を実現する。  
  main ブランチにマージされた際に、バックエンドおよびフロントエンドのデプロイを自動的に実行するように設定した。

  過剰な実行を防ぐため、バックエンドのデプロイは infra ディレクトリ内の資材が更新された場合、  
  フロントエンドのデプロイは frontend ディレクトリ内の資材が更新された場合にのみ実行するように設定した。  
  (ただしいずれも、配下の README.me を除く)

- AWS CloudFormation

  インフラは [AWS CloudFormation](https://aws.amazon.com/jp/cloudformation/)によって構築している。
  そのため、構築の自動化は、CloudFormation スタックの更新によって実現することとした。

  また、CloudFormation テンプレートのサイズ制限（51,200 バイト）を回避する必要から、ネストされたスタック構造を採用した。
  完全に独立したスタックとする選択肢もあったが、親スタックから一括で実行できる点を評価して、ネストされたスタック構造を採用した。

- AWS CLI およびシェルスクリプト

  Lambda 関数のパッケージングにおいて、若干のコマンド実行が必要となるため、GitHub Actions 内でシェルスクリプトを実行することとした。
  infra/deploy.sh にデプロイ用のシェルスクリプトを用意した。これは GitHub Actions 内で実行される。

- OIDC 連携による AWS API 呼び出し

  AWS API 呼び出しについて、AWS シークレットを用いた方法は、万一シークレット情報が流出した場合に第三者が API 呼び出しをできてしまうことから、セキュリティ上非推奨となっている。
  そこで、OIDC 連携を用いて、GitHub の当該リポジトリからのみデプロイを許可するような設定とした。
  infra/infra-oidc.yaml に定義を記載している。

  参考:  
  [アマゾン ウェブ サービスでの OpenID Connect の構成](https://docs.github.com/ja/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)

## 今後の改善ポイント

- 自動テスト
  本来は CICD に自動テストを組み込むべきであるが、本プロジェクトでは、現時点では自動テストを実装していないため割愛している。
  フロントエンドでは [Playwright](https://playwright.dev/)、バックエンドでは [unittest](https://docs.python.org/ja/3/library/unittest.html) などを用いて自動テストを実装すると、
  さらにシステム改修時の負荷を減らし、品質を向上できると考えている。
