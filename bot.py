import asyncio
import json
import os
import sqlite3
import time
from datetime import datetime, timezone

import discord
import feedparser

BASE = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE, "posted.db")

LOCAL_CONFIG = os.path.join(BASE, "config_local.json")
CONFIG_PATH = os.path.join(BASE, "config.json")

with open(CONFIG_PATH) as f:
    config = json.load(f)

local = {}
if os.path.exists(LOCAL_CONFIG):
    with open(LOCAL_CONFIG) as f:
        local = json.load(f)

TOKEN = os.environ.get("EU_BOT_TOKEN") or local.get("token") or config.get("token")
CHANNEL_ID = int(os.environ.get("EU_BOT_CHANNEL_ID") or local.get("channel_id") or config.get("channel_id", 0))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS posted (link TEXT PRIMARY KEY)")
    conn.commit()
    return conn

def is_posted(conn, link):
    return conn.execute("SELECT 1 FROM posted WHERE link = ?", (link,)).fetchone() is not None

def mark_posted(conn, link):
    conn.execute("INSERT OR IGNORE INTO posted (link) VALUES (?)", (link,))
    conn.commit()

def clean_old_entries(conn, max_age_days=30):
    cutoff = time.time() - max_age_days * 86400
    conn.execute("DELETE FROM posted WHERE rowid NOT IN (SELECT rowid FROM posted ORDER BY rowid DESC LIMIT 500)")
    conn.commit()

def fetch_articles(feed_url, max_count=3):
    parsed = feedparser.parse(feed_url)
    entries = []
    for entry in parsed.entries[:max_count]:
        link = entry.get("link", "")
        title = entry.get("title", "").strip()
        if not title or not link:
            continue
        summary = entry.get("summary", "")
        published = entry.get("published", "")
        entries.append({"title": title, "link": link, "summary": summary, "published": published})
    return entries

def build_embed(cat_key, cat_conf, articles):
    embed = discord.Embed(
        title=f"{cat_conf['emoji']} {cat_conf['label']}",
        url="https://europa.eu",
        color=cat_conf["color"],
        timestamp=datetime.now(timezone.utc),
    )
    for a in articles:
        summary = a["summary"][:200].replace("\n", " ") + "…" if len(a["summary"]) > 200 else a["summary"]
        pub = f" · {a['published']}" if a["published"] else ""
        embed.add_field(
            name=a["title"],
            value=f"{summary}\n[[Link]]({a['link']}){pub}",
            inline=False,
        )
    return embed

def build_roundup(all_articles):
    lines = ["# 📰 EU News Roundup\n"]
    for cat_key, cat_conf, articles in all_articles:
        if not articles:
            continue
        lines.append(f"## {cat_conf['emoji']} {cat_conf['label']}")
        for a in articles[:1]:
            lines.append(f"- [{a['title']}]({a['link']})")
        lines.append("")
    return "\n".join(lines)

intents = discord.Intents.default()
intents.message_content = True

class EUBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.db = None

    async def on_ready(self):
        self.db = init_db()
        print(f"Logged in as {self.user}")
        self.loop.create_task(self.poll_loop())

    async def poll_loop(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            print(f"Channel {config['channel_id']} not found")
            return

        while not self.is_closed():
            print(f"[{datetime.now()}] Polling feeds...")
            all_articles = []
            for cat_key, cat_conf in config["categories"].items():
                new_articles = []
                for feed_url in cat_conf["feeds"]:
                    try:
                        articles = await asyncio.to_thread(fetch_articles, feed_url, config["max_articles_per_feed"])
                        for a in articles:
                            if not is_posted(self.db, a["link"]):
                                mark_posted(self.db, a["link"])
                                new_articles.append(a)
                    except Exception as e:
                        print(f"Feed error {feed_url}: {e}")
                if new_articles:
                    all_articles.append((cat_key, cat_conf, new_articles))
                    await channel.send(embed=build_embed(cat_key, cat_conf, new_articles))
                    await asyncio.sleep(1)

            if all_articles:
                clean_old_entries(self.db)

            print(f"  -> Posted {sum(len(a) for _,_,a in all_articles)} new articles")
            await asyncio.sleep(config["poll_interval_minutes"] * 60)

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content == "!eu roundup":
            await message.channel.send("Running roundup…")
            lines = []
            for cat_key, cat_conf in config["categories"].items():
                articles = []
                for feed_url in cat_conf["feeds"]:
                    try:
                        articles.extend(await asyncio.to_thread(fetch_articles, feed_url, 1))
                    except:
                        pass
                if articles:
                    a = articles[0]
                    lines.append(f"**{cat_conf['emoji']} {cat_conf['label']}**: [{a['title']}]({a['link']})")
            await message.channel.send("\n".join(lines) if lines else "No articles fetched.")

if __name__ == "__main__":
    bot = EUBot()
    bot.run(TOKEN)
