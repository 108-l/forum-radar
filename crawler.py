"""
全域多语种极客情报与商业流转捕获引擎 (GitHub Actions 云端自动化单次版)
- 覆盖六维：NodeSeek, V2EX, LowEndTalk(EN), Habr(RU), Lobste.rs, GitHub Trending
- 纯 Python 原生标准库，零外部依赖，极速秒级启动
- 每次运行执行一次完整全域巡检，写入 SQLite (WAL)
- 若有新增帖子，自动更新 latest_digest.txt
"""

import time
import random
import sqlite3
import json
import urllib.request
import xml.etree.ElementTree as ET
import re
from datetime import datetime
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "forum_archive.db")
DIGEST_FILE = os.path.join(BASE_DIR, "latest_digest.txt")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, application/xml, text/xml, text/html, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ru;q=0.5",
}

new_posts_this_run = []


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forum_posts (
            id TEXT PRIMARY KEY,
            source TEXT,
            title TEXT,
            url TEXT,
            author TEXT,
            published_at TEXT,
            content TEXT,
            fetched_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forum_digests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT,
            post_count INTEGER,
            summary TEXT,
            full_content TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON forum_posts(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_published ON forum_posts(published_at)")
    conn.commit()
    conn.close()


def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 请求跳过 ({url}): {e}")
        return None


def fetch_nodeseek():
    url = "https://www.nodeseek.com/rss.xml"
    raw_xml = fetch_url(url)
    if not raw_xml:
        return 0
    try:
        root = ET.fromstring(raw_xml)
        items = root.findall("./channel/item")
    except Exception as e:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    for item in items:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        description = item.findtext("description", "").strip()
        author = item.findtext("author", "") or "community"
        post_id = f"nodeseek_{link.rstrip('/').split('/')[-1]}"

        cursor.execute("SELECT id FROM forum_posts WHERE id = ?", (post_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO forum_posts (id, source, title, url, author, published_at, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, "NodeSeek", title, link, author, pub_date, description, datetime.now().isoformat()))
            new_count += 1
            new_posts_this_run.append({"source": "NodeSeek", "title": title, "url": link, "published_at": pub_date})
    conn.commit()
    conn.close()
    return new_count


def fetch_v2ex():
    url = "https://www.v2ex.com/api/topics/latest.json"
    raw_json = fetch_url(url)
    if not raw_json:
        return 0
    try:
        topics = json.loads(raw_json)
    except Exception as e:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    for topic in topics:
        topic_id = f"v2ex_{topic.get('id')}"
        title = topic.get("title", "").strip()
        url = topic.get("url", "")
        author = topic.get("member", {}).get("username", "")
        created = str(topic.get("created", ""))
        content = topic.get("content", "")

        cursor.execute("SELECT id FROM forum_posts WHERE id = ?", (topic_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO forum_posts (id, source, title, url, author, published_at, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (topic_id, "V2EX", title, url, author, created, content, datetime.now().isoformat()))
            new_count += 1
            new_posts_this_run.append({"source": "V2EX", "title": title, "url": url, "published_at": created})
    conn.commit()
    conn.close()
    return new_count


def fetch_lowendtalk():
    url = "https://lowendtalk.com/discussions/feed.rss"
    raw_xml = fetch_url(url)
    if not raw_xml:
        return 0
    try:
        root = ET.fromstring(raw_xml)
        items = root.findall("./channel/item")
    except Exception as e:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    for item in items:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        description = item.findtext("description", "").strip()
        clean_id = link.rstrip('/').split('/')[-1].split('?')[0]
        post_id = f"lowendtalk_{clean_id}"

        cursor.execute("SELECT id FROM forum_posts WHERE id = ?", (post_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO forum_posts (id, source, title, url, author, published_at, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, "LowEndTalk(EN)", title, link, "LET", pub_date, description[:500], datetime.now().isoformat()))
            new_count += 1
            new_posts_this_run.append({"source": "LowEndTalk(EN)", "title": title, "url": link, "published_at": pub_date})
    conn.commit()
    conn.close()
    return new_count


def fetch_habr():
    url = "https://habr.com/ru/rss/hub/infosecurity/"
    raw_xml = fetch_url(url)
    if not raw_xml:
        return 0
    try:
        root = ET.fromstring(raw_xml)
        items = root.findall("./channel/item")
    except Exception as e:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    for item in items:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        description = item.findtext("description", "").strip()
        author = item.findtext("author", "") or "habr_author"
        clean_url = link.split("?")[0]
        post_id = f"habr_{clean_url.rstrip('/').split('/')[-1]}"

        cursor.execute("SELECT id FROM forum_posts WHERE id = ?", (post_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO forum_posts (id, source, title, url, author, published_at, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, "Habr(RU)", title, clean_url, author, pub_date, description[:500], datetime.now().isoformat()))
            new_count += 1
            new_posts_this_run.append({"source": "Habr(RU)", "title": title, "url": clean_url, "published_at": pub_date})
    conn.commit()
    conn.close()
    return new_count


def fetch_lobsters():
    url = "https://lobste.rs/rss"
    raw_xml = fetch_url(url)
    if not raw_xml:
        return 0
    try:
        root = ET.fromstring(raw_xml)
        items = root.findall("./channel/item")
    except Exception as e:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    for item in items:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        author = item.findtext("author", "") or "lobsters"
        post_id = f"lobsters_{link.rstrip('/').split('/')[-1]}"

        cursor.execute("SELECT id FROM forum_posts WHERE id = ?", (post_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO forum_posts (id, source, title, url, author, published_at, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, "Lobste.rs", title, link, author, pub_date, title, datetime.now().isoformat()))
            new_count += 1
            new_posts_this_run.append({"source": "Lobste.rs", "title": title, "url": link, "published_at": pub_date})
    conn.commit()
    conn.close()
    return new_count


def fetch_github_trending():
    url = "https://github.com/trending?since=daily"
    html = fetch_url(url)
    if not html:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_count = 0
    articles = html.split('<article class="Box-row">')[1:]
    today_str = datetime.now().strftime("%Y-%m-%d")

    for art in articles:
        repo_match = re.search(r'href="\/([a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+)"', art)
        if not repo_match:
            continue
        repo_path = repo_match.group(1).strip()
        if repo_path.startswith("features/") or repo_path.startswith("site/"):
            continue

        repo_url = f"https://github.com/{repo_path}"
        post_id = f"github_{today_str}_{repo_path.replace('/', '_')}"

        desc_match = re.search(r'<p class="col-9 color-fg-muted my-1 pr-4">(.*?)<\/p>', art, re.S)
        description = desc_match.group(1).strip() if desc_match else "No description"
        description = re.sub(r'<.*?>', '', description).strip()

        stars_today_match = re.search(r'([0-9,]+)\s+stars today', art)
        stars_today = stars_today_match.group(1).strip() if stars_today_match else "0"

        title = f"[GitHub Hot] {repo_path} (今日新增 ⭐{stars_today}): {description[:60]}"

        cursor.execute("SELECT id FROM forum_posts WHERE id = ?", (post_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO forum_posts (id, source, title, url, author, published_at, content, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (post_id, "GitHub", title, repo_url, repo_path.split('/')[0], today_str, f"Stars: {stars_today} | {description}", datetime.now().isoformat()))
            new_count += 1
            new_posts_this_run.append({"source": "GitHub", "title": title, "url": repo_url, "published_at": today_str})

    conn.commit()
    conn.close()
    return new_count


def generate_digest():
    if not new_posts_this_run:
        print("本轮无新增帖子，无需生成新快报。")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = len(new_posts_this_run)
    counts_by_source = {}
    for p in new_posts_this_run:
        src = p["source"]
        counts_by_source[src] = counts_by_source.get(src, 0) + 1

    source_stat_str = ", ".join(f"{k}: {v}篇" for k, v in counts_by_source.items())

    categories = []
    titles_text = " ".join(p["title"] for p in new_posts_this_run).lower()
    if counts_by_source.get("LowEndTalk(EN)", 0) > 0:
        categories.append("🌐 英文全球特价主机与海外算力一手行情")
    if counts_by_source.get("Habr(RU)", 0) > 0:
        categories.append("🇷🇺 俄区底层流量混淆、Telegram逆向与安全对抗")
    if counts_by_source.get("Lobste.rs", 0) > 0:
        categories.append("🦞 全球邀请制底层系统架构与极客讨论")
    if counts_by_source.get("GitHub", 0) > 0:
        categories.append("🐙 今日全球最火 GitHub 暴涨开源黑科技")
    if any(k in titles_text for k in ["gpt", "claude", "ai", "team", "openai"]):
        categories.append("🤖 AI商业车位招募与大模型落地风向")
    if any(k in titles_text for k in ["9929", "cmin2", "cn2", "vps", "aws", "lightsail", "出", "收"]):
        categories.append("💻 国内云服务线路波动与二手转让")
    if not categories:
        categories.append("常规开发日常与软硬件技术交流")

    summary_bullets = "；".join(categories)

    card_lines = [
        "=" * 65,
        f"📡 【全域六维极客情报 快报】({now_str})",
        f"📊 本批次共捕获 {count} 篇新帖 ({source_stat_str})",
        "-" * 65,
        f"🧠 【核心动向速览】：{summary_bullets}",
        "-" * 65,
        "📋 【最新抓取清单】：",
    ]

    for idx, p in enumerate(new_posts_this_run, 1):
        card_lines.append(f"{idx:02d}. [{p['source']}] {p['title']}")
        card_lines.append(f"    🔗 {p['url']}")

    card_lines.append("=" * 65)
    full_card_text = "\n".join(card_lines)

    print("\n" + full_card_text + "\n")

    with open(DIGEST_FILE, "w", encoding="utf-8") as f:
        f.write(full_card_text)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO forum_digests (generated_at, post_count, summary, full_content)
        VALUES (?, ?, ?, ?)
    """, (now_str, count, summary_bullets, full_card_text))
    conn.commit()
    conn.close()


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 启动单次全域巡检...")
    init_db()

    ns = fetch_nodeseek()
    time.sleep(1)
    v2 = fetch_v2ex()
    time.sleep(1)
    let = fetch_lowendtalk()
    time.sleep(1)
    hb = fetch_habr()
    time.sleep(1)
    lb = fetch_lobsters()
    time.sleep(1)
    gh = fetch_github_trending()

    print(f"巡检完成: NS({ns}), V2({v2}), LET({let}), Habr({hb}), Lobsters({lb}), GH({gh}) | 新增: {len(new_posts_this_run)} 篇")
    if new_posts_this_run:
        generate_digest()


if __name__ == "__main__":
    main()
