"""Topic-level content gap analysis from sitemaps.

Reads the XML sitemaps of your site and your competitors, turns every URL
slug into a topic, and compares how deeply each site covers each topic.
No page is crawled: only sitemap files are downloaded.
"""
import gzip
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

USER_AGENT = "content-gap-crawler/1.0 (+https://github.com/marketing-MEER/content-gap-crawler)"

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with", "without", "at", "by", "is", "are",
    "your", "you", "my", "how", "what", "why", "when", "where", "which", "who", "do", "does", "can", "vs",
    "from", "into", "about", "this", "that", "it", "its", "be", "use", "using", "get", "make", "new",
    # generic content words that say nothing about the topic
    "guide", "guides", "tips", "ways", "best", "top", "ultimate", "complete", "examples", "example",
    "ideas", "list", "step", "steps", "easy", "simple", "free", "online", "beginners", "beginner",
    "blog", "post", "posts", "article", "articles", "page", "pages", "html", "htm", "php", "index",
    "en", "us", "uk", "de", "category", "tag", "tags", "author", "news", "resources", "learn",
}
YEAR = re.compile(r"^(19|20)\d{2}$")
# Site pages that are not content topics.
UTILITY = {"contact", "contact-us", "about", "about-us", "pricing", "plans", "login", "log-in", "signin", "sign-in",
           "signup", "sign-up", "register", "privacy", "privacy-policy", "terms", "terms-of-service", "imprint",
           "impressum", "careers", "jobs", "cart", "checkout", "account", "search", "demo", "home", "sitemap",
           "cookie-policy", "cookies", "legal", "press", "team", "partners", "affiliates", "support", "help"}


# ---------------------------------------------------------------- sitemaps

def _get(url: str, session) -> bytes:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.content
    return gzip.decompress(data) if url.endswith(".gz") or data[:2] == b"\x1f\x8b" else data


def _parse(content: bytes) -> tuple[list[str], list[str]]:
    """Return (page urls, child sitemap urls)."""
    root = ET.fromstring(content)
    locs = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
    return ([], locs) if root.tag.endswith("sitemapindex") else (locs, [])


def discover_sitemaps(domain: str, session) -> list[str]:
    base = domain if domain.startswith("http") else f"https://{domain}"
    base = base.rstrip("/")
    try:
        robots = session.get(base + "/robots.txt", timeout=15)
        found = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots.text) if robots.ok else []
    except requests.RequestException:
        found = []
    return found or [base + "/sitemap.xml"]


def load_site(source: str, max_urls: int = 5000, delay: float = 0.5, session=None) -> list[str]:
    """source = local .xml/.xml.gz/.txt file, a sitemap URL, or a bare domain (sitemaps found via robots.txt)."""
    path = Path(source)
    if path.exists():
        data = path.read_bytes()
        if path.suffix == ".gz":
            data = gzip.decompress(data)
        if path.suffix == ".txt":
            return [l.strip() for l in data.decode("utf-8").splitlines() if l.strip()][:max_urls]
        pages, children = _parse(data)
        for child in children:  # local sitemap index pointing to local files next to it
            child_path = path.parent / Path(urlparse(child).path).name
            if child_path.exists():
                pages += load_site(str(child_path), max_urls, delay, session)
        return pages[:max_urls]

    session = session or requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    queue = [source] if source.startswith("http") and (".xml" in source or source.endswith(".gz")) \
        else discover_sitemaps(source, session)
    pages, seen = [], set()
    while queue and len(pages) < max_urls:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            found, children = _parse(_get(url, session))
        except (requests.RequestException, ET.ParseError):
            continue
        pages += found
        queue += children
        time.sleep(delay)
    return list(dict.fromkeys(pages))[:max_urls]


def site_label(source: str, urls: list[str]) -> str:
    host = urlparse(urls[0]).netloc if urls else (urlparse(source).netloc or Path(source).stem)
    return host[4:] if host.startswith("www.") else host


# ---------------------------------------------------------------- topics

def slug_words(url: str) -> list[str]:
    """Raw words from the last path segment (folders like /blog/ are dropped). Utility pages give []."""
    parts = [p for p in urlparse(url).path.split("/") if p]
    if not parts:
        return []
    last = re.sub(r"\.(html?|php|aspx)$", "", parts[-1].lower())
    if last in UTILITY:
        return []
    words = re.findall(r"[a-z0-9äöüß]+", last)
    return [w for w in words if w not in STOPWORDS and not YEAR.match(w) and not w.isdigit() and len(w) > 1]


def normaliser(vocabulary: set[str]):
    """Fold word forms only into forms that really occur in the URLs:
    'templates' -> 'template' and 'forecasting' -> 'forecast' if those exist, while 'sales' stays 'sales'."""
    def norm(word: str) -> str:
        for suffix, repl in (("ies", "y"), ("es", ""), ("s", ""), ("ing", "")):
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                base = word[: -len(suffix)] + repl
                if base in vocabulary:
                    return base
        return word
    return norm


def slug_tokens(url: str, norm=None) -> list[str]:
    words = slug_words(url)
    return [norm(w) for w in words] if norm else words


def phrases(tokens: list[str]) -> list[str]:
    bigrams = [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]
    return bigrams + tokens


def assign_topics(urls_by_site: dict[str, list[str]], min_pages: int = 3) -> pd.DataFrame:
    """Each URL gets the most widely used phrase it contains (bigram first, then single word)."""
    vocabulary = {w for urls in urls_by_site.values() for u in urls for w in slug_words(u)}
    norm = normaliser(vocabulary)
    rows = [(site, url, slug_tokens(url, norm)) for site, urls in urls_by_site.items() for url in urls]
    df_count = Counter()
    for _, _, toks in rows:
        df_count.update(set(phrases(toks)))

    def best(toks):
        tokens = set(toks)
        bigrams = [p for p in phrases(toks) if " " in p and df_count[p] >= min_pages]
        if bigrams:
            return max(bigrams, key=lambda p: (df_count[p], p))
        singles = [t for t in tokens if df_count[t] >= min_pages]
        return max(singles, key=lambda t: (df_count[t], t)) if singles else "(other)"

    return pd.DataFrame([{"site": s, "url": u, "topic": best(t)} for s, u, t in rows if t])


# ---------------------------------------------------------------- gaps

def coverage(pages: pd.DataFrame, me: str) -> pd.DataFrame:
    """Topic x site page counts, with the gap status of every topic for `me`."""
    matrix = pages[pages["topic"] != "(other)"].pivot_table(index="topic", columns="site", values="url",
                                                             aggfunc="count", fill_value=0)
    if me not in matrix.columns:
        matrix[me] = 0
    rivals = [c for c in matrix.columns if c != me]
    matrix = matrix[[me] + rivals]
    matrix["competitors_covering"] = (matrix[rivals] > 0).sum(axis=1)
    matrix["competitor_avg_pages"] = matrix[rivals].mean(axis=1).round(1)
    matrix["competitor_max_pages"] = matrix[rivals].max(axis=1)

    def status(row):
        mine = row[me]
        if mine == 0:
            return "missing" if row["competitors_covering"] >= 2 else "untapped"
        if mine < row["competitor_avg_pages"] / 2:
            return "thin"
        if mine >= row["competitor_max_pages"]:
            return "leading"
        return "covered"

    matrix["status"] = matrix.apply(status, axis=1)
    # Depth gap: pages you'd need to match the deepest competitor on the topic.
    matrix["pages_to_match_leader"] = (matrix["competitor_max_pages"] - matrix[me]).clip(lower=0)
    order = {"missing": 0, "thin": 1, "untapped": 2, "covered": 3, "leading": 4}
    matrix = matrix.reset_index()
    matrix["_o"] = matrix["status"].map(order)
    return matrix.sort_values(["_o", "pages_to_match_leader", "competitors_covering"],
                              ascending=[True, False, False]).drop(columns="_o").reset_index(drop=True)


def example_urls(pages: pd.DataFrame, topics: list[str], exclude_site: str, n: int = 3) -> pd.DataFrame:
    """A few competitor URLs per gap topic, to study before writing."""
    sub = pages[pages["topic"].isin(topics) & (pages["site"] != exclude_site)]
    return (sub.groupby("topic").head(n).sort_values(["topic", "site"])[["topic", "site", "url"]]
            .reset_index(drop=True))
