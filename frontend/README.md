# janken hockey frontend

## 概要

Janken Hockey の SPA アプリケーションコード

- ユーザー/パスワードでのユーザー登録およびログイン機能
- CPU 対戦、オンライン 2 人対戦(WebSocket 通信)
  - ゲームの盤面は Vue コンポーネント内で SVG 形式で描画
- ルームによる対戦相手マッチング機能
- ゲーム結果の保存

## ディレクトリ構成

```
frontend/
├── public/favicon.ico    アイコンファイル
├── src/                  ソースコード
│   ├── api/              API通信関連コード
│   ├── assets/           画像、CSS等の静的アセット
│   ├── components/       画面の部品に対応するVueコンポーネント
│   ├── constants/        定数定義(じゃんけんの手、メッセージ)
│   ├── util/             ユーティリティ関数(ログイン、ログアウト処理関連)
├── index.html            HTMLテンプレート
├── main.js               エントリポイント
├── App.vue               ルートコンポーネント
├── *.vue                 各画面に対応するVueコンポーネント
├── route.js              ルーティング設定
├── package.json          npmパッケージ設定ファイル
└── vite.config.js        Vite設定ファイル(ビルドツール)


```

## 前提条件

- npm がインストールされていること
- Node.js (>18)がインストールされていること

## 構築手順

### デプロイ実行

1.  [infra/README.md](../infra/README.md) の「GitHub Acitions を利用する場合」を参照

2.  デプロイ成功したら、CloudFront の URL にアクセス
    例： `https://xxxxxxxxxxxx.cloudfront.net/`

### ローカルでテスト実行

1. 下記コマンドを実行

```sh
npm run dev
```

2. 表示された URL にアクセス
   例: `http://localhost:5173/`

## 技術スタック

- Language / Framework

  - Vue 3

- ビルドツール

  - Vite

- パッケージマネージャー

  - npm

- CI/CD

  - GitHub Actions
