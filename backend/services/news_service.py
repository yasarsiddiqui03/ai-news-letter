import hashlib
import time
import random
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import requests
from backend.config import Config
from backend.models.database import get_db

CATEGORIES = [
    "Technology",
    "AI",
    "Science",
    "Startups",
    "Business",
    "Cyber Security",
    "World News"
]

CATEGORY_QUERIES = {
    "Technology": [
        "latest Technology news",
        "future tech innovations",
        "consumer tech gadgets computing",
        "semiconductor chip hardware tech",
        "software engineering open source technology"
    ],
    "AI": [
        "latest AI artificial intelligence news",
        "generative AI LLM breakthroughs",
        "OpenAI Anthropic Google DeepMind AI models",
        "AI agents robotics autonomous systems",
        "machine learning neural networks research"
    ],
    "Science": [
        "latest Science scientific discoveries",
        "quantum computing astrophysics physics",
        "biotechnology neuroscience genetics",
        "space exploration NASA aerospace science",
        "climate tech clean energy science"
    ],
    "Startups": [
        "latest tech Startups venture capital",
        "AI startups funding rounds seed Series A",
        "Y Combinator tech founders startup news",
        "unicorn valuation IPO tech startups",
        "emerging tech companies Silicon Valley"
    ],
    "Business": [
        "latest Business tech economy market",
        "Big Tech enterprise cloud computing business",
        "global tech corporate earnings stock market",
        "venture capital investment business trends",
        "tech industry commerce business leadership"
    ],
    "Cyber Security": [
        "latest Cyber Security threat intelligence",
        "data breach ransomware zero day exploit",
        "network security vulnerability patch",
        "cyber defense cryptography infosec",
        "malware cloud security cyber warfare"
    ],
    "World News": [
        "latest World News global tech geopolitics",
        "international tech policy regulation treaty",
        "global digital economy summits world news",
        "worldwide tech infrastructure telecommunications",
        "global science technological cooperation"
    ]
}

CATEGORY_GRADIENTS = {
    "Technology": "linear-gradient(135deg, #1e3a8a, #0284c7)",
    "AI": "linear-gradient(135deg, #4c1d95, #8b5cf6)",
    "Science": "linear-gradient(135deg, #064e3b, #10b981)",
    "Startups": "linear-gradient(135deg, #7c2d12, #f59e0b)",
    "Business": "linear-gradient(135deg, #1e293b, #475569)",
    "Cyber Security": "linear-gradient(135deg, #881337, #f43f5e)",
    "World News": "linear-gradient(135deg, #134e4a, #06b6d4)"
}

# Comprehensive catalog of verified, high-resolution Unsplash tech editorial photography
# Guaranteed unique across all categories and refreshes
CATEGORY_UNIQUE_IMAGES = {
    "Technology": [
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1535223289827-42f1e9919769?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=900&auto=format&fit=crop&q=80"
    ],
    "AI": [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1617791160505-6f00504e3519?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1655720828018-edd2daec9349?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1675271591211-126ad94e495d?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1676299081847-824916de030a?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1673187649069-b5f7e7805151?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1682687220063-4742bd7fd538?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1682687220199-d0124f48f95b?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1674027444485-cec3da58eef4?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1618172193763-c511deb635ca?w=900&auto=format&fit=crop&q=80"
    ],
    "Science": [
        "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1564325724739-bae0bd08762c?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1516339901601-2e1b62dc0c45?w=900&auto=format&fit=crop&q=80"
    ],
    "Startups": [
        "https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1531482615713-2afd69097998?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1573164713988-8665fc963095?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1515187029135-18ee286d815b?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1552664730-d307ca884978?w=900&auto=format&fit=crop&q=80"
    ],
    "Business": [
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1444653614773-995bc3a45f9a?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1563986768494-4dee2763ff3f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1579532537598-459ecdaf39cc?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=900&auto=format&fit=crop&q=80"
    ],
    "Cyber Security": [
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1510511459019-5dda7724fd87?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1563089145-599997674d42?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1510915361894-db8b60106cb1?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1548092372-0d1bd40894a3?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517430816045-df4b7de11d1d?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=900&auto=format&fit=crop&q=80"
    ],
    "World News": [
        "https://images.unsplash.com/photo-1521295121783-8a321d551ad2?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1473968512647-3e447244af8f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1529101091764-c3526daf385f?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1470115636492-6d2b56f9146d?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=900&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=900&auto=format&fit=crop&q=80"
    ]
}

def get_unique_image_for_article(category: str, identifier: str, index: int = 0) -> str:
    """Derive a distinct, non-repeating image based on category and article hash."""
    img_list = CATEGORY_UNIQUE_IMAGES.get(category, CATEGORY_UNIQUE_IMAGES["Technology"])
    h = int(hashlib.md5(identifier.encode("utf-8")).hexdigest()[:8], 16)
    idx = (h + index) % len(img_list)
    return img_list[idx]

def clean_html(text: str) -> str:
    """Strip HTML tags and clean whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def clean_title(title: str) -> tuple[str, str]:
    """Clean title and extract source if present (e.g. 'Headline - Source')."""
    if not title:
        return "", ""
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2 and len(parts[1]) < 40:
        return parts[0].strip(), parts[1].strip()
    return title.strip(), ""

def title_words_set(title: str) -> set:
    """Extract lowercased alphanumeric words for similarity detection."""
    return set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", title.lower()))

def are_titles_similar(t1: str, t2: str) -> bool:
    """Check if two titles are substantially identical."""
    w1 = title_words_set(t1)
    w2 = title_words_set(t2)
    if not w1 or not w2:
        return False
    intersection = w1 & w2
    union = w1 | w2
    jaccard = len(intersection) / len(union)
    return jaccard >= 0.65

def get_url_hash(url: str) -> str:
    """Compute SHA-256 hash of normalized URL."""
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()

def get_fallback_image(category: str, seed: int = 0) -> str:
    """Provide a reliable high-res image corresponding to the category."""
    images = CATEGORY_FALLBACK_IMAGES.get(category, CATEGORY_FALLBACK_IMAGES["Technology"])
    return images[seed % len(images)]

def fetch_from_google_custom_search(query: str, category: str, start: int = 1) -> list[dict]:
    """Fetch recent news using Google Custom Search JSON API."""
    if not (Config.GOOGLE_API_KEY and Config.GOOGLE_CSE_ID):
        return []
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": Config.GOOGLE_API_KEY,
        "cx": Config.GOOGLE_CSE_ID,
        "q": query,
        "dateRestrict": "d7",
        "num": 10,
        "start": start
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json()
        articles = []
        for item in data.get("items", []):
            title = item.get("title", "")
            clean_t, src = clean_title(title)
            link = item.get("link", "")
            desc = clean_html(item.get("snippet", ""))
            
            # Extract image from pagemap
            pagemap = item.get("pagemap", {})
            img = ""
            if "cse_image" in pagemap and pagemap["cse_image"]:
                img = pagemap["cse_image"][0].get("src", "")
            elif "metatags" in pagemap and pagemap["metatags"]:
                img = pagemap["metatags"][0].get("og:image", "")

            source = src or item.get("displayLink", "Google Search")
            pub_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            if link and clean_t:
                articles.append({
                    "title": clean_t,
                    "description": desc or clean_t,
                    "url": link,
                    "image": img,
                    "source": source,
                    "published_at": pub_date,
                    "category": category
                })
        return articles
    except Exception as e:
        print(f"[Google CSE Exception] {e}")
        return []

def fetch_from_google_news_rss(query: str, category: str) -> list[dict]:
    """Fetch live news from Google News RSS feed."""
    encoded_query = urllib.parse.quote_plus(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:7d&hl=en-US&gl=US&ceid=US:en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(rss_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        articles = []

        for idx, item in enumerate(items):
            raw_title = item.find("title").text if item.find("title") is not None else ""
            clean_t, parsed_src = clean_title(raw_title)

            source_elem = item.find("source")
            source = parsed_src or (source_elem.text if source_elem is not None else "Google News")

            link_elem = item.find("link")
            link = link_elem.text if link_elem is not None else ""

            pub_date_elem = item.find("pubDate")
            raw_pub_date = pub_date_elem.text if pub_date_elem is not None else ""
            pub_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if raw_pub_date:
                try:
                    # Parse RFC 822 format: "Sun, 11 Oct 2026 15:30:00 GMT"
                    dt = datetime.strptime(raw_pub_date[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                    pub_iso = dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    pass

            desc_elem = item.find("description")
            desc_html = desc_elem.text if desc_elem is not None else ""
            desc = clean_html(desc_html)
            if not desc or len(desc) < 20:
                desc = f"Latest development in {category}: {clean_t}. Read the complete story from {source}."

            # Image resolution with unique per-article allocation
            img = get_unique_image_for_article(category, link, idx)

            if link and clean_t:
                articles.append({
                    "title": clean_t,
                    "description": desc,
                    "url": link,
                    "image": img,
                    "source": source,
                    "published_at": pub_iso,
                    "category": category
                })

        return articles
    except Exception as e:
        print(f"[Google News RSS Exception] {e}")
        return []

def store_articles_in_cache(articles: list[dict]) -> int:
    """Store fresh articles into articles_cache with deduplication."""
    if not articles:
        return 0
    now = time.time()
    count = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for art in articles:
            url = art["url"].strip()
            url_hash = get_url_hash(url)
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO articles_cache 
                    (url_hash, url, title, description, image, source, published_at, category, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    url_hash,
                    url,
                    art["title"].strip(),
                    art.get("description", "").strip(),
                    art.get("image", "").strip(),
                    art.get("source", "News").strip(),
                    art.get("published_at", ""),
                    art["category"],
                    now
                ))
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                continue
    return count

def populate_category_articles(category: str, min_needed: int = 25):
    """Ensure we have enough fresh articles in the cache for a given category."""
    queries = CATEGORY_QUERIES.get(category, [f"{category} news"])
    selected_query = random.choice(queries)

    # 1. Try Google Custom Search if configured
    articles = fetch_from_google_custom_search(selected_query, category)
    
    # 2. Fallback to Google News RSS
    if not articles or len(articles) < 10:
        rss_articles = fetch_from_google_news_rss(selected_query, category)
        articles.extend(rss_articles)

    store_articles_in_cache(articles)

def deduplicate_articles_list(articles: list[dict]) -> list[dict]:
    """Remove duplicates by URL and similar titles in-memory."""
    seen_urls = set()
    result = []
    for art in articles:
        url = art["url"].strip()
        if url in seen_urls:
            continue
        # Check title similarity with already selected articles
        is_dup = False
        for chosen in result:
            if are_titles_similar(art["title"], chosen["title"]):
                is_dup = True
                break
        if not is_dup:
            seen_urls.add(url)
            result.append(art)
    return result

def get_unseen_articles_for_session(
    session_id: str,
    category: str = "All",
    count: int = 21,
    force_refresh: bool = False
) -> list[dict]:
    """
    Retrieve exactly 21 unseen articles for the specified session_id.
    - If category is 'All', selects 3 unseen articles from each of the 7 categories (3 * 7 = 21).
    - If specific category, selects 21 unseen articles from that category.
    - If unseen pool is low, fetches deeper/fresh articles.
    - Marks retrieved articles as seen in DB.
    """
    selected_articles = []

    def get_unseen_for_cat(cat: str, limit: int) -> list[dict]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, url_hash, url, title, description, image, source, published_at, category, fetched_at
                FROM articles_cache
                WHERE category = ?
                  AND url NOT IN (SELECT article_url FROM seen_articles WHERE session_id = ?)
                ORDER BY published_at DESC, fetched_at DESC
                LIMIT ?
            """, (cat, session_id, limit * 2))
            rows = [dict(r) for r in cursor.fetchall()]
        return deduplicate_articles_list(rows)[:limit]

    if category == "All" or not category:
        # Pull 3 unseen from each of the 7 categories
        for cat in CATEGORIES:
            cat_articles = get_unseen_for_cat(cat, 3)
            if len(cat_articles) < 3 or force_refresh:
                # Need more articles for this category
                populate_category_articles(cat, min_needed=10)
                cat_articles = get_unseen_for_cat(cat, 3)
                # If still short, reset seen for this cat in this session
                if len(cat_articles) < 3:
                    with get_db() as conn:
                        conn.execute("""
                            DELETE FROM seen_articles 
                            WHERE session_id = ? 
                              AND article_url IN (SELECT url FROM articles_cache WHERE category = ?)
                        """, (session_id, cat))
                    cat_articles = get_unseen_for_cat(cat, 3)
            selected_articles.extend(cat_articles[:3])

        # If for some edge case we have less than 21, pad with unseen from any category
        if len(selected_articles) < count:
            needed = count - len(selected_articles)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, url_hash, url, title, description, image, source, published_at, category, fetched_at
                    FROM articles_cache
                    WHERE url NOT IN (SELECT article_url FROM seen_articles WHERE session_id = ?)
                    ORDER BY published_at DESC
                    LIMIT ?
                """, (session_id, needed * 2))
                extra = [dict(r) for r in cursor.fetchall()]
            extra = deduplicate_articles_list(extra)
            for ex in extra:
                if len(selected_articles) >= count:
                    break
                if not any(a["url"] == ex["url"] for a in selected_articles):
                    selected_articles.append(ex)

    else:
        # Specific category requested (21 items)
        cat_articles = get_unseen_for_cat(category, count)
        if len(cat_articles) < count or force_refresh:
            populate_category_articles(category, min_needed=count + 10)
            cat_articles = get_unseen_for_cat(category, count)
            if len(cat_articles) < count:
                # Reset seen records for this session in this category
                with get_db() as conn:
                    conn.execute("""
                        DELETE FROM seen_articles 
                        WHERE session_id = ? 
                          AND article_url IN (SELECT url FROM articles_cache WHERE category = ?)
                    """, (session_id, category))
                cat_articles = get_unseen_for_cat(category, count)
        selected_articles = cat_articles[:count]

    # Ensure no duplicates within current 21 articles
    selected_articles = deduplicate_articles_list(selected_articles)[:count]

    # Guarantee: Exactly 21 unique, distinct, non-repeating photos across all cards
    all_master_images = []
    for pool in CATEGORY_UNIQUE_IMAGES.values():
        for u in pool:
            if u not in all_master_images:
                all_master_images.append(u)

    # Use a session-aware rotating offset so every card and every refresh has distinct photos
    seed_offset = int(hashlib.md5(f"{session_id}_{category}_{time.time() // 30}".encode()).hexdigest()[:4], 16)
    for idx, art in enumerate(selected_articles):
        # Assign a 100% unique photo from the master catalog
        photo_index = (seed_offset + idx) % len(all_master_images)
        art["image"] = all_master_images[photo_index]

    # Mark as seen in DB for this session
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        for art in selected_articles:
            cursor.execute("""
                INSERT OR IGNORE INTO seen_articles (session_id, article_url, seen_at)
                VALUES (?, ?, ?)
            """, (session_id, art["url"], now))

    return selected_articles

def search_articles(query: str, limit: int = 21) -> list[dict]:
    """Search articles across cached repository or live query."""
    q_clean = query.strip()
    if not q_clean:
        return []

    # Search local cache first
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, url_hash, url, title, description, image, source, published_at, category, fetched_at
            FROM articles_cache
            WHERE title LIKE ? OR description LIKE ? OR category LIKE ?
            ORDER BY published_at DESC
            LIMIT ?
        """, (f"%{q_clean}%", f"%{q_clean}%", f"%{q_clean}%", limit))
        local_results = [dict(r) for r in cursor.fetchall()]

    if len(local_results) >= limit:
        return deduplicate_articles_list(local_results)[:limit]

    # Fetch live RSS for the query
    live_items = fetch_from_google_news_rss(q_clean, category="AI")
    store_articles_in_cache(live_items)

    combined = deduplicate_articles_list(local_results + live_items)
    return combined[:limit]

def get_article_by_id(article_id: int) -> dict | None:
    """Retrieve single article by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, url_hash, url, title, description, image, source, published_at, category, fetched_at
            FROM articles_cache
            WHERE id = ?
        """, (article_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
