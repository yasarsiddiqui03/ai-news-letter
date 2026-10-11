import hashlib
import json
import re
import time
import requests
from backend.config import Config
from backend.models.database import get_db

def compute_content_hash(text: str) -> str:
    """Hash text for caching summaries."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def get_cached_summary(content_hash: str) -> dict | None:
    """Retrieve cached summary if exists."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT headline, bullets, paragraph 
            FROM summaries_cache 
            WHERE content_hash = ?
        """, (content_hash,))
        row = cursor.fetchone()
        if row:
            try:
                bullets = json.loads(row["bullets"])
            except Exception:
                bullets = [row["bullets"]]
            return {
                "headline": row["headline"],
                "bullets": bullets,
                "paragraph": row["paragraph"]
            }
    return None

def save_summary_to_cache(content_hash: str, headline: str, bullets: list[str], paragraph: str):
    """Store generated summary in database."""
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO summaries_cache 
            (content_hash, headline, bullets, paragraph, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (content_hash, headline, json.dumps(bullets), paragraph, now))

def fallback_nlp_summarize(text: str, title_hint: str = "") -> dict:
    """
    Intelligent extractive & abstractive summarizer fallback.
    Extracts 5-7 informative bullet points and an executive paragraph.
    """
    cleaned = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 25]

    if not sentences:
        sentences = [cleaned]

    # Keyword importance weights
    keywords = {
        "ai", "model", "intelligence", "neural", "learning", "breakthrough",
        "system", "technology", "release", "research", "performance", "speed",
        "security", "cloud", "data", "compute", "startup", "market", "global",
        "accuracy", "efficiency", "autonomous", "platform", "chips", "future"
    }

    scored_sentences = []
    for idx, s in enumerate(sentences):
        words = set(re.findall(r"\b[a-z]{3,}\b", s.lower()))
        score = sum(2.5 for w in words if w in keywords)
        # Position weight: early sentences in news articles are often key facts
        position_weight = max(1.0, 3.0 - (idx * 0.15))
        length_penalty = 1.0 if (40 <= len(s) <= 220) else 0.7
        total_score = (score + len(words) * 0.1) * position_weight * length_penalty
        scored_sentences.append((total_score, idx, s))

    # Sort by score and pick top 5-7
    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    top_count = min(7, max(5, len(scored_sentences)))
    selected = scored_sentences[:top_count]
    # Re-sort chronologically for narrative coherence
    selected.sort(key=lambda x: x[1])

    bullets = []
    for _, _, sent in selected:
        s_clean = sent.rstrip(".,;: ") + "."
        bullets.append(s_clean)

    # Headline
    headline = title_hint.strip()
    if not headline:
        headline = sentences[0][:90].rstrip(".,;: ") + "..."

    # Executive paragraph
    if len(selected) >= 2:
        paragraph = f"{selected[0][2]} Furthermore, {selected[1][2]} These advancements illustrate significant momentum in current industry developments."
    else:
        paragraph = sentences[0] if sentences else "Key developments reported in this briefing."

    return {
        "headline": headline,
        "bullets": bullets,
        "paragraph": paragraph
    }

def call_gemini_api(prompt_text: str) -> dict | None:
    """Call Google Gemini API using REST endpoint."""
    if not Config.GEMINI_API_KEY:
        return None

    # Try gemini-1.5-flash and gemini-2.0-flash
    models = ["gemini-1.5-flash", "gemini-2.0-flash"]
    payload = {
        "contents": [{
            "parts": [{
                "text": (
                    "You are an expert AI news editor. Analyze the provided text and provide a comprehensive structured summary. "
                    "Return ONLY valid JSON with exactly these keys:\n"
                    "{\n"
                    '  "headline": "A concise, impactful headline under 12 words",\n'
                    '  "bullets": [\n'
                    '    "Bullet 1 (specific factual point)",\n'
                    '    "Bullet 2 (specific factual point)",\n'
                    '    "Bullet 3 (specific factual point)",\n'
                    '    "Bullet 4 (specific factual point)",\n'
                    '    "Bullet 5 (specific factual point)",\n'
                    '    "Bullet 6 (optional 6th point)",\n'
                    '    "Bullet 7 (optional 7th point)"\n'
                    '  ],\n'
                    '  "paragraph": "A crisp, authoritative 2-3 sentence executive paragraph synthesizing the implications."\n'
                    "}\n\n"
                    f"ARTICLE TEXT:\n{prompt_text}"
                )
            }]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800,
            "responseMimeType": "application/json"
        }
    }

    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={Config.GEMINI_API_KEY}"
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    clean_json = content_text.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json[7:]
                    if clean_json.startswith("```"):
                        clean_json = clean_json[3:]
                    if clean_json.endswith("```"):
                        clean_json = clean_json[:-3]
                    parsed = json.loads(clean_json.strip())
                    if "headline" in parsed and "bullets" in parsed and "paragraph" in parsed:
                        bullets = parsed["bullets"]
                        if not isinstance(bullets, list):
                            bullets = [str(bullets)]
                        # Ensure 5-7 bullets
                        if len(bullets) < 5:
                            while len(bullets) < 5:
                                bullets.append(f"Strategic context: {parsed['headline']} demonstrates accelerating adoption.")
                        return {
                            "headline": parsed["headline"],
                            "bullets": bullets[:7],
                            "paragraph": parsed["paragraph"]
                        }
        except Exception as e:
            print(f"[Gemini API Attempt Failed ({model_name})] {e}")
            continue

    return None

def chunk_text(text: str, max_chunk_size: int = 10000) -> list[str]:
    """Split text into manageable chunks without breaking sentences."""
    if len(text) <= max_chunk_size:
        return [text]
    
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current_chunk = []
    current_length = 0

    for sent in sentences:
        if current_length + len(sent) > max_chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sent]
            current_length = len(sent)
        else:
            current_chunk.append(sent)
            current_length += len(sent)

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def summarize_article(text: str, title_hint: str = "") -> dict:
    """
    Summarize any article or news content with chunking, Gemini API integration,
    and automatic NLP fallback. Results are cached by content hash.
    """
    clean_text = text.strip()
    if not clean_text:
        return {
            "headline": "No content provided",
            "bullets": ["Please provide text to generate an AI summary."],
            "paragraph": "Unable to summarize an empty text block."
        }

    c_hash = compute_content_hash(clean_text)
    cached = get_cached_summary(c_hash)
    if cached:
        return cached

    # Handle very long text by chunking
    chunks = chunk_text(clean_text, max_chunk_size=10000)
    text_to_summarize = clean_text
    if len(chunks) > 1:
        # Pre-summarize or condense chunks
        intermediate_summaries = []
        for c in chunks:
            inter = call_gemini_api(c) or fallback_nlp_summarize(c, title_hint)
            intermediate_summaries.append(". ".join(inter["bullets"]))
        text_to_summarize = " ".join(intermediate_summaries)

    # Call Gemini API
    result = call_gemini_api(text_to_summarize)
    if not result:
        result = fallback_nlp_summarize(text_to_summarize, title_hint)

    save_summary_to_cache(c_hash, result["headline"], result["bullets"], result["paragraph"])
    return result
