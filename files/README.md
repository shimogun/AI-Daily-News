# AI News Digest

生成AI関連ニュースを毎朝メールで配信するシステムです。

## セットアップ手順

### 1. リポジトリを作成

GitHubで新しいリポジトリを作成し、このファイルを全てプッシュしてください。

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/ai-news-digest.git
git push -u origin main
```

### 2. GitHub Secrets を設定

GitHubリポジトリの **Settings → Secrets and variables → Actions** から以下を追加：

| Secret名            | 説明                        | 例                          |
|---------------------|-----------------------------|-----------------------------|
| `ANTHROPIC_API_KEY` | Anthropic APIキー            | `sk-ant-...`               |
| `SMTP_USER`         | 送信元GmailアドレスSMTP     | `yourname@gmail.com`        |
| `SMTP_PASS`         | Gmailアプリパスワード        | `xxxx xxxx xxxx xxxx`       |
| `DIGEST_TO`         | 受信メールアドレス           | `yourname@gmail.com`        |

### 3. Gmail アプリパスワードの取得

1. Googleアカウント → セキュリティ → 2段階認証をオン
2. 「アプリパスワード」を検索 → 新しいパスワードを生成
3. 生成された16桁のパスワードを `SMTP_PASS` に設定

### 4. 動作確認

GitHub Actions タブ → 「AI News Digest」→ 「Run workflow」で手動実行して確認。

## カスタマイズ

### 配信時間の変更

`.github/workflows/daily_digest.yml` の cron を変更：

```yaml
# 毎朝 6:00 JST に変更する場合
- cron: '0 21 * * *'
```

### RSSソースの追加・変更

`digest.py` の `RSS_FEEDS` リストを編集してください。

### 記事数の変更

`digest.py` の `MAX_ARTICLES` を変更（デフォルト: 10件）。

## コスト目安

- GitHub Actions: 無料（月2000分まで）
- Claude API (Haiku): 約 $0.5〜1 / 月
- Gmail SMTP: 無料

## ローカルでのテスト

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."
export SMTP_USER="yourname@gmail.com"
export SMTP_PASS="your-app-password"
export DIGEST_TO="yourname@gmail.com"

python digest.py
```
