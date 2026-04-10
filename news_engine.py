"""
news_engine.py — AI News Aggregator + Bias Detector
Fetches real news from RSS feeds, runs Gemini AI analysis:
  - Political bias (left / center-left / center / center-right / right)
  - Emotional tone (neutral / sensational / fear / anger / hope)
  - Fact vs opinion ratio
  - Loaded language detection
  - Cross-source comparison on same story
  - Credibility signals
"""

import json
import re
import time
import hashlib
import feedparser
import httpx
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import google.generativeai as genai


# ── News sources with known bias labels (based on AllSides / Ad Fontes) ────────
NEWS_SOURCES = {
    # Left / Center-Left
    "npr":           {"name": "NPR",              "url": "https://feeds.npr.org/1001/rss.xml",                           "allsides": "center-left",  "emoji": "📻"},
    "guardian":      {"name": "The Guardian",     "url": "https://www.theguardian.com/world/rss",                        "allsides": "center-left",  "emoji": "🇬🇧"},
    "huffpost":      {"name": "HuffPost",         "url": "https://www.huffpost.com/section/front-page/feed",             "allsides": "left",         "emoji": "📰"},
    "vox":           {"name": "Vox",              "url": "https://www.vox.com/rss/index.xml",                            "allsides": "left",         "emoji": "📖"},

    # Center
    "ap":            {"name": "AP News",          "url": "https://rsshub.app/apnews/topics/apf-topnews",                 "allsides": "center",       "emoji": "📡"},
    "reuters":       {"name": "Reuters",          "url": "https://feeds.reuters.com/reuters/topNews",                    "allsides": "center",       "emoji": "🌐"},
    "bbc":           {"name": "BBC News",         "url": "http://feeds.bbci.co.uk/news/world/rss.xml",                   "allsides": "center",       "emoji": "🎙️"},
    "csmonitor":     {"name": "CS Monitor",       "url": "https://rss.csmonitor.com/feeds/top",                          "allsides": "center",       "emoji": "📰"},

    # Right / Center-Right
    "wsj":           {"name": "Wall St Journal",  "url": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",                  "allsides": "center-right", "emoji": "💼"},
    "foxnews":       {"name": "Fox News",         "url": "https://moxie.foxnews.com/google-publisher/world.xml",         "allsides": "right",        "emoji": "🦊"},
    "nypost":        {"name": "NY Post",          "url": "https://nypost.com/feed/",                                     "allsides": "right",        "emoji": "📰"},
    "dailywire":     {"name": "Daily Wire",       "url": "https://feeds.dailywire.com/rss.xml",                          "allsides": "right",        "emoji": "📻"},

    # International / Tech
    "techcrunch":    {"name": "TechCrunch",       "url": "https://techcrunch.com/feed/",                                  "allsides": "center-left",  "emoji": "💻"},
    "ars":           {"name": "Ars Technica",     "url": "https://feeds.arstechnica.com/arstechnica/index",               "allsides": "center",       "emoji": "🔬"},
    "aljazeera":     {"name": "Al Jazeera",       "url": "https://www.aljazeera.com/xml/rss/all.xml",                    "allsides": "center-left",  "emoji": "🌍"},
}

ALLSIDES_ORDER = ["left", "center-left", "center", "center-right", "right"]

BIAS_COLORS = {
    "left":          "#3b82f6",
    "center-left":   "#60a5fa",
    "center":        "#22c55e",
    "center-right":  "#f87171",
    "right":         "#ef4444",
}

TONE_COLORS = {
    "neutral":       "#94a3b8",
    "analytical":    "#a78bfa",
    "sensational":   "#f97316",
    "fear":          "#ef4444",
    "anger":         "#dc2626",
    "hope":          "#22c55e",
    "concern":       "#f59e0b",
}


# ── Data structures ────────────────────────────────────────────────────────────
@dataclass
class NewsArticle:
    id:          str
    title:       str
    summary:     str
    url:         str
    source_id:   str
    source_name: str
    published:   str
    allsides:    str              # known bias from AllSides
    fetched_at:  str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BiasAnalysis:
    article_id:         str
    title:              str
    source:             str
    detected_bias:      str       # left / center-left / center / center-right / right
    bias_confidence:    int       # 0-100
    tone:               str       # neutral / sensational / fear / anger / hope / concern
    tone_confidence:    int
    fact_ratio:         int       # 0-100 (% factual vs opinion)
    loaded_words:       list[str] # emotionally loaded language found
    framing:            str       # how the story is framed (1 sentence)
    missing_context:    str       # what context is notably absent
    headline_bias:      str       # analysis of headline specifically
    credibility_score:  int       # 0-100
    summary_neutral:    str       # neutral rewrite of the headline
    flags:              list[str] # specific issues: clickbait / opinion-as-fact / etc.


@dataclass
class StoryCluster:
    topic:        str
    articles:     list[NewsArticle]
    analyses:     list[BiasAnalysis]
    consensus:    str             # what all sources agree on
    divergence:   str             # where sources diverge most
    missing_voice: str            # which perspective is missing


# ── RSS fetcher ────────────────────────────────────────────────────────────────
def fetch_source(source_id: str, max_articles: int = 8) -> list[NewsArticle]:
    """Fetch articles from a single RSS source."""
    source = NEWS_SOURCES[source_id]
    try:
        feed = feedparser.parse(source["url"])
        articles = []
        for entry in feed.entries[:max_articles]:
            title   = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            # Strip HTML tags from summary
            summary = re.sub(r"<[^>]+>", "", summary)[:500]
            url     = entry.get("link", "")
            pub     = entry.get("published", entry.get("updated", datetime.now().isoformat()))

            if not title or len(title) < 10:
                continue

            uid = hashlib.md5(f"{source_id}{url}".encode()).hexdigest()[:12]
            articles.append(NewsArticle(
                id=uid,
                title=title,
                summary=summary,
                url=url,
                source_id=source_id,
                source_name=source["name"],
                published=pub,
                allsides=source["allsides"],
            ))
        return articles
    except Exception as e:
        return []


def fetch_multiple_sources(
    source_ids: list[str],
    max_per_source: int = 6,
    on_progress: callable = None,
) -> list[NewsArticle]:
    """Fetch from multiple sources with progress callback."""
    all_articles = []
    for i, sid in enumerate(source_ids):
        articles = fetch_source(sid, max_per_source)
        all_articles.extend(articles)
        if on_progress:
            on_progress(i + 1, len(source_ids), NEWS_SOURCES[sid]["name"], len(articles))
        time.sleep(0.3)   # be polite to servers
    return all_articles


# ── Gemini bias analysis ───────────────────────────────────────────────────────
def analyse_article(article: NewsArticle, api_key: str) -> BiasAnalysis:
    """Run full bias analysis on a single article using Gemini."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"temperature": 0.1, "max_output_tokens": 800},
    )

    prompt = f"""You are a non-partisan media literacy expert. Analyse this news article for bias, tone, and credibility.

SOURCE: {article.source_name} (AllSides rating: {article.allsides})
HEADLINE: {article.title}
SUMMARY: {article.summary[:400]}

Return ONLY valid JSON (no markdown):
{{
  "detected_bias": "<left|center-left|center|center-right|right>",
  "bias_confidence": <0-100>,
  "tone": "<neutral|analytical|sensational|fear|anger|hope|concern>",
  "tone_confidence": <0-100>,
  "fact_ratio": <0-100 percent factual vs opinion>,
  "loaded_words": ["list", "of", "emotionally", "charged", "words", "found"],
  "framing": "<one sentence: how is this story being framed?>",
  "missing_context": "<one sentence: what important context is absent?>",
  "headline_bias": "<one sentence: specific analysis of the headline>",
  "credibility_score": <0-100>,
  "summary_neutral": "<rewrite the headline in completely neutral language>",
  "flags": ["clickbait"|"opinion-as-fact"|"missing-sources"|"loaded-language"|"false-balance"|"cherry-picking"]
}}

Be specific and accurate. Base detection on actual language used, not assumed source bias."""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
    except Exception:
        data = {
            "detected_bias": article.allsides,
            "bias_confidence": 60,
            "tone": "neutral",
            "tone_confidence": 60,
            "fact_ratio": 70,
            "loaded_words": [],
            "framing": "Standard news reporting.",
            "missing_context": "Unable to analyse.",
            "headline_bias": "Unable to analyse headline.",
            "credibility_score": 70,
            "summary_neutral": article.title,
            "flags": [],
        }

    return BiasAnalysis(
        article_id=article.id,
        title=article.title,
        source=article.source_name,
        detected_bias=data.get("detected_bias", article.allsides),
        bias_confidence=int(data.get("bias_confidence", 60)),
        tone=data.get("tone", "neutral"),
        tone_confidence=int(data.get("tone_confidence", 60)),
        fact_ratio=int(data.get("fact_ratio", 70)),
        loaded_words=data.get("loaded_words", [])[:8],
        framing=data.get("framing", ""),
        missing_context=data.get("missing_context", ""),
        headline_bias=data.get("headline_bias", ""),
        credibility_score=int(data.get("credibility_score", 70)),
        summary_neutral=data.get("summary_neutral", article.title),
        flags=data.get("flags", []),
    )


def analyse_batch(
    articles: list[NewsArticle],
    api_key: str,
    on_progress: callable = None,
    max_articles: int = 20,
) -> list[BiasAnalysis]:
    """Analyse a batch of articles with progress callback."""
    analyses = []
    articles_to_analyse = articles[:max_articles]
    for i, article in enumerate(articles_to_analyse):
        analysis = analyse_article(article, api_key)
        analyses.append(analysis)
        if on_progress:
            on_progress(i + 1, len(articles_to_analyse), article.title[:50])
        time.sleep(0.5)  # rate limit respect
    return analyses


def cluster_stories(
    articles: list[NewsArticle],
    analyses: list[BiasAnalysis],
    api_key: str,
    top_n: int = 5,
) -> list[StoryCluster]:
    """Group articles by topic and compare cross-source coverage."""
    if not articles:
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"temperature": 0.2, "max_output_tokens": 1500},
    )

    titles_list = "\n".join([f"{i+1}. [{a.source_name}] {a.title}" for i, a in enumerate(articles[:40])])

    prompt = f"""Group these news headlines into {top_n} main story clusters.
Each cluster should represent the SAME underlying news event covered by multiple sources.

HEADLINES:
{titles_list}

Return ONLY valid JSON:
{{
  "clusters": [
    {{
      "topic": "<2-5 word topic name>",
      "article_indices": [<list of 1-based indices of headlines in this cluster>],
      "consensus": "<what ALL sources covering this agree on>",
      "divergence": "<where sources diverge most — specific differences>",
      "missing_voice": "<which political perspective is notably absent>"
    }}
  ]
}}

Only include clusters with 2+ articles. Pick the {top_n} most covered stories."""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        data = json.loads(raw)
        clusters_raw = data.get("clusters", [])
    except Exception:
        return []

    # Build analysis lookup
    analysis_map = {a.article_id: a for a in analyses}
    clusters = []

    for c in clusters_raw[:top_n]:
        indices = [i - 1 for i in c.get("article_indices", []) if 0 < i <= len(articles)]
        cluster_articles = [articles[i] for i in indices if i < len(articles)]
        cluster_analyses = [analysis_map[a.id] for a in cluster_articles if a.id in analysis_map]

        if len(cluster_articles) < 2:
            continue

        clusters.append(StoryCluster(
            topic=c.get("topic", "News Story"),
            articles=cluster_articles,
            analyses=cluster_analyses,
            consensus=c.get("consensus", ""),
            divergence=c.get("divergence", ""),
            missing_voice=c.get("missing_voice", ""),
        ))

    return clusters


def bias_spectrum_summary(analyses: list[BiasAnalysis]) -> dict:
    """Compute aggregate bias statistics across all analysed articles."""
    if not analyses:
        return {}

    bias_counts = {b: 0 for b in ALLSIDES_ORDER}
    tone_counts: dict[str, int] = {}
    total_credibility = 0
    total_fact_ratio  = 0
    all_loaded: list[str] = []
    all_flags: list[str]  = []

    for a in analyses:
        bias = a.detected_bias
        if bias in bias_counts:
            bias_counts[bias] += 1
        tone_counts[a.tone] = tone_counts.get(a.tone, 0) + 1
        total_credibility += a.credibility_score
        total_fact_ratio  += a.fact_ratio
        all_loaded.extend(a.loaded_words)
        all_flags.extend(a.flags)

    # Most common loaded words
    word_freq: dict[str, int] = {}
    for w in all_loaded:
        word_freq[w.lower()] = word_freq.get(w.lower(), 0) + 1
    top_loaded = sorted(word_freq.items(), key=lambda x: -x[1])[:15]

    # Most common flags
    flag_freq: dict[str, int] = {}
    for f in all_flags:
        flag_freq[f] = flag_freq.get(f, 0) + 1

    return {
        "total":            len(analyses),
        "bias_distribution": bias_counts,
        "tone_distribution": tone_counts,
        "avg_credibility":  round(total_credibility / len(analyses), 1),
        "avg_fact_ratio":   round(total_fact_ratio  / len(analyses), 1),
        "top_loaded_words": top_loaded,
        "flag_distribution": flag_freq,
        "most_biased_source": max(analyses, key=lambda a: abs(ALLSIDES_ORDER.index(a.detected_bias) - 2)).source if analyses else "",
        "most_neutral_source": min(analyses, key=lambda a: abs(ALLSIDES_ORDER.index(a.detected_bias) - 2)).source if analyses else "",
    }
