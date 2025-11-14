import feedparser
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, date
from utils import categorize_article, clean_text

CONFIG_FILE = "config.json"
CACHE_FILE = "cache.json"

KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml",
    "llm", "large language model", "agent", "raw q&a",
    "deep learning", "neural", "microsoft", "google", "openai",
    "anthropic", "research", "transformer", "diffusion"
]


def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def score_article(title: str, summary: str) -> int:
    """Keyword-basierte Relevanzbewertung."""
    text = f"{title.lower()} {summary.lower()}"
    score = 0

    for kw in KEYWORDS:
        if kw in text:
            score += 3

    score += len(summary) // 300  # längere Artikel leicht bevorzugen

    return score


def fetch_feeds(sources, cache):
    """Sammelt alle Artikel der letzten 48h + updated den Cache."""
    new_articles = []
    now = datetime.utcnow()
    fresh_limit = now - timedelta(hours=48)

    for url in sources:
        feed = feedparser.parse(url)
        source_title = feed.feed.get("title", "Unbekannte Quelle")

        for entry in feed.entries:
            link = entry.get("link")
            if not link:
                continue

            # Zeitstempel
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if published_parsed:
                published = datetime(*published_parsed[:6])
            else:
                # Fallback: Immer erlauben
                published = now

            title = entry.get("title", "").strip()
            summary = clean_text(entry.get("summary", ""))

            article = {
                "title": title,
                "link": link,
                "summary": summary,
                "source": source_title,
                "published": published.isoformat(),
                "category": categorize_article(title, summary),
                "score": score_article(title, summary)
            }

            # Immer scrappen, aber nur neue markieren
            is_new = link not in cache and published > fresh_limit

            if is_new:
                new_articles.append(article)
                cache[link] = True

    return new_articles, cache


def pick_best_articles_per_feed(articles):
    """Wählt pro Quelle den besten/hochwertigsten Artikel."""
    best = {}
    for a in articles:
        src = a["source"]
        if src not in best or a["score"] > best[src]["score"]:
            best[src] = a
    return list(best.values())


def send_email(sender, receiver, password, new_articles, fallback_articles):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 Dein täglicher AI Digest – {date.today().isoformat()}"
    msg["From"] = sender
    msg["To"] = receiver

    html = ""

    html += "<h2>🧠 Neue Artikel der letzten 48 Stunden</h2>"
    if not new_articles:
        html += "<p>Keine neuen Artikel gefunden – aber hier sind die besten Empfehlungen!</p>"
    else:
        for a in new_articles:
            html += f"""
            <hr>
            <b>{a['title']}</b><br>
            <i>{a['category']}</i><br>
            <p>{a['summary'][:250]}...</p>
            <a href="{a['link']}">Weiterlesen</a>
            <br><small>Quelle: {a['source']}</small>
            """

    html += "<h2>⭐ Beste Artikel pro Quelle</h2>"
    for a in fallback_articles:
        html += f"""
        <hr>
        <b>{a['title']}</b><br>
        <i>{a['category']}</i><br>
        <p>{a['summary'][:250]}...</p>
        <a href="{a['link']}">Weiterlesen</a>
        <br><small>Quelle: {a['source']}</small>
        """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())


def main():
    config = load_json(CONFIG_FILE)
    cache = load_json(CACHE_FILE)

    sender = os.getenv("EMAIL_USER", config["email"]["sender"])
    receiver = os.getenv("EMAIL_RECEIVER", config["email"]["receiver"])
    password = os.getenv("EMAIL_PASS", config["email"]["app_password"])

    new_articles, updated_cache = fetch_feeds(config["sources"], cache)

    # Fallback: beste pro Quelle
    best_articles = pick_best_articles_per_feed(new_articles or cache_based_articles(updated_cache))

    send_email(sender, receiver, password, new_articles, best_articles)

    save_json(CACHE_FILE, updated_cache)


def cache_based_articles(cache):
    """Fallback: Holt Artikel aus dem Cache (nur Titel/Link)."""
    items = []
    for link in cache.keys():
        items.append({
            "title": "📝 Artikel (aus Cache)",
            "link": link,
            "summary": "Summary nicht verfügbar.",
            "source": "Unbekannt",
            "category": "Info",
            "score": 0
        })
    return items


if __name__ == "__main__":
    main()