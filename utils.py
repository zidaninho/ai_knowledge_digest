import re

def categorize_article(title, summary):
    text = (title + " " + summary).lower()
    if any(k in text for k in ["tutorial", "learn", "guide", "how to"]):
        return "Lerninhalt"
    elif any(k in text for k in ["framework", "release", "library"]):
        return "Open Source / Tools"
    elif any(k in text for k in ["paper", "research", "study"]):
        return "Research"
    elif any(k in text for k in ["trend", "future", "market"]):
        return "AI Trends"
    return "Allgemein Wissenswert"

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
