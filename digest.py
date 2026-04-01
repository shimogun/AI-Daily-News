"""
AI News Digest - 毎朝メール配信スクリプト
"""
import os
import smtplib
import json
import re
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
import requests


# ── ソース設定 ──────────────────────────────────────────────
RSS_FEEDS = [
    {"name": "TechCrunch AI",  "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "The Verge AI",   "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "Wired AI",       "url": "https://www.wired.com/feed/tag/ai/latest/rss"},
    {"name": "MIT Tech Review","url": "https://www.technologyreview.com/feed/"},
    {"name": "arXiv cs.AI",    "url": "https://rss.arxiv.org/rss/cs.AI"},
    {"name": "arXiv cs.LG",    "url": "https://rss.arxiv.org/rss/cs.LG"},
    {"name": "arXiv cs.CL",    "url": "https://rss.arxiv.org/rss/cs.CL"},
]

AI_KEYWORDS = [
    "AI", "artificial intelligence", "LLM", "GPT", "Claude", "Gemini",
    "machine learning", "deep learning", "neural", "generative", "ChatGPT",
    "OpenAI", "Anthropic", "Google DeepMind",
]

MAX_ARTICLES = 10
HOURS_LOOKBACK = 26


def fetch_articles():
    articles = []
    cutoff = datetime.utcnow() - timedelta(hours=HOURS_LOOKBACK)

    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            is_arxiv = "arxiv" in feed_info["url"]

            for entry in feed.entries[:20]:
                published = None
                for date_field in ["published_parsed", "updated_parsed"]:
                    if hasattr(entry, date_field) and getattr(entry, date_field):
                        published = datetime(*getattr(entry, date_field)[:6])
                        break

                if published and published < cutoff:
                    continue

                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))[:500]
                link = entry.get("link", "")

                if not is_arxiv:
                    text = (title + " " + summary).lower()
                    if not any(kw.lower() in text for kw in AI_KEYWORDS):
                        continue

                articles.append({
                    "source": feed_info["name"],
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "published": published.strftime("%Y-%m-%d %H:%M") if published else "不明"
                })

        except Exception as e:
            print(f"[WARN] {feed_info['name']} の取得に失敗: {e}")

    seen = set()
    unique = []
    for a in articles:
        key = a["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique[:30]


def summarize_with_claude(articles):
    api_key = os.environ["ANTHROPIC_API_KEY"]

    articles_text = "\n\n".join([
        f"[{i+1}] {a['source']}\nタイトル: {a['title']}\n概要: {a['summary']}\nURL: {a['link']}"
        for i, a in enumerate(articles)
    ])

    prompt = f"""以下は生成AI関連の最新ニュース記事リストです。

{articles_text}

タスク：
1. 最も重要・注目度が高い記事を{MAX_ARTICLES}件選んでください
2. 各記事を日本語で3〜4文に要約してください
3. 重要度順に並べてください

必ず以下のJSON形式のみで回答してください（他のテキスト不要）：
{{
  "digest": [
    {{
      "rank": 1,
      "source": "ソース名",
      "title_ja": "日本語タイトル",
      "summary_ja": "日本語要約（3〜4文）",
      "url": "記事URL",
      "category": "モデル発表|ツール|研究|ビジネス|規制|その他"
    }}
  ],
  "headline": "本日のAIニュース全体を一言で表すキャッチコピー（20文字以内）"
}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-haiku-4-5",
            "max_tokens": 3000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )
    response.raise_for_status()
    content = response.json()["content"][0]["text"]

    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"JSONを取得できませんでした: {content[:200]}")


CATEGORY_EMOJI = {
    "モデル発表": "🤖",
    "ツール": "🔧",
    "研究": "📄",
    "ビジネス": "💼",
    "規制": "⚖️",
    "その他": "📌"
}

def build_email_html(digest_data):
    today = datetime.now().strftime("%Y年%-m月%-d日")
    headline = digest_data.get("headline", "本日の生成AIニュース")
    items = digest_data.get("digest", [])

    articles_html = ""
    for item in items:
        emoji = CATEGORY_EMOJI.get(item.get("category", ""), "📌")
        articles_html += f"""
        <tr>
          <td style="padding:20px 24px;border-bottom:1px solid #f0f0f0;">
            <div style="display:flex;align-items:flex-start;gap:12px;">
              <span style="font-size:20px;line-height:1;">{emoji}</span>
              <div>
                <div style="font-size:11px;color:#888;margin-bottom:4px;">{item.get('source','')} · {item.get('category','')}</div>
                <div style="font-size:16px;font-weight:600;color:#1a1a1a;line-height:1.4;margin-bottom:8px;">{item.get('title_ja','')}</div>
                <div style="font-size:14px;color:#444;line-height:1.7;">{item.get('summary_ja','')}</div>
                <a href="{item.get('url','')}" style="display:inline-block;margin-top:10px;font-size:12px;color:#5B4DE8;text-decoration:none;font-weight:500;">記事を読む →</a>
              </div>
            </div>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8f7ff;font-family:-apple-system,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr><td style="background:linear-gradient(135deg,#5B4DE8,#9B59B6);border-radius:16px 16px 0 0;padding:32px;text-align:center;">
          <div style="font-size:11px;color:rgba(255,255,255,.7);letter-spacing:2px;margin-bottom:8px;">AI NEWS DIGEST</div>
          <div style="font-size:26px;font-weight:700;color:#fff;">{headline}</div>
          <div style="font-size:13px;color:rgba(255,255,255,.75);margin-top:10px;">{today} · {len(items)}本のニュース</div>
        </td></tr>
        <tr><td style="background:#fff;border-radius:0 0 16px 16px;">
          <table width="100%" cellpadding="0" cellspacing="0">{articles_html}</table>
        </td></tr>
        <tr><td style="padding:20px 0;text-align:center;">
          <div style="font-size:12px;color:#aaa;">AI News Digestにより自動配信</div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_email(html_body, subject):
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    to_addr   = os.environ["DIGEST_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_user
    msg["To"]      = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_addr, msg.as_string())

    print(f"✅ 送信完了 → {to_addr}")


def main():
    print("📡 記事収集中...")
    articles = fetch_articles()
    print(f"  {len(articles)}件取得")

    if not articles:
        print("⚠️ 記事なし。終了します。")
        return

    print("🤖 Claude APIで要約中...")
    digest_data = summarize_with_claude(articles)

    today = datetime.now().strftime("%-m/%-d")
    headline = digest_data.get("headline", "本日の生成AIニュース")
    subject = f"【AI Digest {today}】{headline}"

    print("📧 メール送信中...")
    send_email(build_email_html(digest_data), subject)


if __name__ == "__main__":
    main()
