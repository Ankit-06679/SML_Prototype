"""
Reddit scraper using Arctic Shift API (Pushshift replacement).
No credentials, no rate limits, full historical data.
API docs: https://arctic-shift.photon-reddit.com/api-docs
"""
import requests
import json
import os
import time
import sys
from datetime import datetime
from urllib.parse import quote_plus

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SUBREDDITS, SEARCH_KEYWORDS, SCRAPE_LIMIT

ARCTIC_BASE = "https://arctic-shift.photon-reddit.com/api"

HEADERS = {
    "User-Agent": "SML-Research-Bot/1.0",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def safe_get(url: str, params: dict = None, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            print(f"  [WARN] HTTP {resp.status_code} — {url}")
            time.sleep(2)
        except Exception as e:
            print(f"  [ERROR] {e} — retry {attempt+1}/{retries}")
            time.sleep(3)
    return {}


def fetch_post_comments(post_id: str, limit: int = 15) -> list:
    """Fetch comments for a post via Arctic Shift."""
    data = safe_get(f"{ARCTIC_BASE}/comments/search", params={
        "link_id": post_id,
        "limit": limit,
    })
    comments = []
    for item in data.get("data", []):
        body = item.get("body", "")
        if not body or body in ("[deleted]", "[removed]"):
            continue
        comments.append({
            "id": item.get("id", ""),
            "text": body,
            "score": item.get("score", 0),
            "author": item.get("author", "[deleted]"),
            "created_utc": datetime.utcfromtimestamp(
                item.get("created_utc", 0)
            ).isoformat(),
            "flair": item.get("author_flair_text") or "",
        })
    return comments


def search_posts_arctic(subreddit: str, keyword: str, limit: int = SCRAPE_LIMIT) -> list:
    """Search posts in a subreddit using Arctic Shift full-text search."""
    data = safe_get(f"{ARCTIC_BASE}/posts/search", params={
        "subreddit": subreddit,
        "query": keyword,
        "limit": min(limit, 100),
    })

    posts = []
    for item in data.get("data", []):
        body = item.get("selftext", "")
        if body in ("[deleted]", "[removed]"):
            body = ""

        post_id = item.get("id", "")
        comments = []
        if post_id:
            comments = fetch_post_comments(post_id)
            time.sleep(0.3)

        posts.append({
            "id": post_id,
            "subreddit": subreddit,
            "keyword": keyword,
            "title": item.get("title", ""),
            "text": body,
            "url": f"https://www.reddit.com{item.get('permalink', '')}",
            "score": item.get("score", 0),
            "upvote_ratio": item.get("upvote_ratio", 0),
            "num_comments": item.get("num_comments", 0),
            "author": item.get("author", "[deleted]"),
            "author_flair": item.get("author_flair_text") or "",
            "post_flair": item.get("link_flair_text") or "",
            "awards": item.get("total_awards_received", 0),
            "created_utc": datetime.utcfromtimestamp(
                item.get("created_utc", 0)
            ).isoformat(),
            "is_original_content": item.get("is_original_content", False),
            "comments": comments,
        })
        print(f"    + {item.get('title','')[:70]}")

    return posts


def fetch_subreddit_top(subreddit: str, limit: int = 50) -> list:
    """Fetch top posts from a subreddit for broader coverage."""
    RELEVANCE_TERMS = [
        "asthma", "mepolizumab", "nucala", "biologic", "inhaler",
        "breathing", "eosinophil", "steroid", "respiratory", "lung",
        "allerg", "immune", "injection", "flare", "biologic",
    ]

    data = safe_get(f"{ARCTIC_BASE}/posts/search", params={
        "subreddit": subreddit,
        "limit": limit,
    })

    posts = []
    for item in data.get("data", []):
        combined = (item.get("title", "") + " " + item.get("selftext", "")).lower()
        if not any(t in combined for t in RELEVANCE_TERMS):
            continue

        body = item.get("selftext", "")
        if body in ("[deleted]", "[removed]"):
            body = ""

        post_id = item.get("id", "")
        comments = fetch_post_comments(post_id) if post_id else []
        time.sleep(0.3)

        posts.append({
            "id": post_id,
            "subreddit": subreddit,
            "keyword": "feed:top",
            "title": item.get("title", ""),
            "text": body,
            "url": f"https://www.reddit.com{item.get('permalink', '')}",
            "score": item.get("score", 0),
            "upvote_ratio": item.get("upvote_ratio", 0),
            "num_comments": item.get("num_comments", 0),
            "author": item.get("author", "[deleted]"),
            "author_flair": item.get("author_flair_text") or "",
            "post_flair": item.get("link_flair_text") or "",
            "awards": item.get("total_awards_received", 0),
            "created_utc": datetime.utcfromtimestamp(
                item.get("created_utc", 0)
            ).isoformat(),
            "is_original_content": item.get("is_original_content", False),
            "comments": comments,
        })
        print(f"    [top] {item.get('title','')[:70]}")

    return posts


def run_scraper(output_path: str = "data/raw_posts.json"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Load existing posts for resume support
    all_posts = []
    seen_ids = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            all_posts = json.load(f)
            seen_ids = {p["id"] for p in all_posts}
        print(f"Resuming — {len(all_posts)} existing posts loaded.")

    def add_and_save(new_posts):
        added = 0
        for p in new_posts:
            if p["id"] and p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_posts.append(p)
                added += 1
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, indent=2, ensure_ascii=False)
        return added

    # Phase 1: Keyword search
    print("\n" + "="*60)
    print("PHASE 1: Keyword search via Arctic Shift")
    print("="*60)
    for subreddit in SUBREDDITS:
        for keyword in SEARCH_KEYWORDS:
            print(f"\n>> r/{subreddit} | '{keyword}'")
            posts = search_posts_arctic(subreddit, keyword, limit=SCRAPE_LIMIT)
            added = add_and_save(posts)
            print(f"   +{added} new (total: {len(all_posts)})")
            time.sleep(1)

    # Phase 2: Top posts per subreddit
    print("\n" + "="*60)
    print("PHASE 2: Top posts per subreddit")
    print("="*60)
    for subreddit in SUBREDDITS:
        print(f"\n>> r/{subreddit}/top")
        posts = fetch_subreddit_top(subreddit, limit=50)
        added = add_and_save(posts)
        print(f"   +{added} new (total: {len(all_posts)})")
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE")
    print(f"Total unique posts : {len(all_posts)}")
    print(f"Saved to           : {output_path}")
    print(f"{'='*60}")
    return all_posts


if __name__ == "__main__":
    run_scraper()
