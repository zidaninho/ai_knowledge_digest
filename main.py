import feedparser
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from utils import categorize_article, clean_text

CONFIG_FILE = "config.json"
CACHE_FILE = "cache.json"

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def fetch_feeds(sources, cache):
    new_articles = []
    for url in sources:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            link = entry.link
            if link not in cache:
                title = entry.title
                summary = clean_text(entry.summary if 'summary' in entry else '')
                category = categorize_article(title, summary)
                new_articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "category": category,
                    "source": feed.feed.title
                })
                cache[link] = True
    return new_articles, cache

def send_email(sender, receiver, password, articles):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 Dein täglicher AI Digest – {date.today().isoformat()}"
    msg["From"] = sender
    msg["To"] = receiver

    if not articles:
        html_content = "<p>Heute keine neuen Artikel. 📭</p>"
    else:
        html_content = "<h2>Neue KI-Lerninhalte & Insights</h2>"
        for a in articles:
            html_content += f"""
            <hr>
            <b>{a['title']}</b><br>
            <i>{a['category']}</i><br>
            <p>{a['summary'][:200]}...</p>
            <a href="{a['link']}">Weiterlesen</a>
            <br><small>Quelle: {a['source']}</small><br>
            """
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())

def main():
    config = load_json(CONFIG_FILE)
    cache = load_json(CACHE_FILE)

    # Nutze GitHub Actions Secrets, falls vorhanden
    sender = os.getenv("EMAIL_USER", config["email"]["sender"])
    receiver = config["email"]["receiver"]
    password = os.getenv("EMAIL_PASS", config["email"]["app_password"])

    new_articles, updated_cache = fetch_feeds(config["sources"], cache)

    if new_articles:
        send_email(sender, receiver, password, new_articles)

    save_json(CACHE_FILE, updated_cache)

if __name__ == "__main__":
    main()
