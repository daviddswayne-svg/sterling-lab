"""Reads the CURRENT Swiss Re Institute sigma report for the Bedrock Director.

Before this module the Director was fed a hardcoded sentence labelled "Sigma 2025 Outlook", and the only
report on disk was a 2024 PDF: the report was never actually read.

How it works
  * sigma_source.json pins the report (title, date, open PDF link). Swiss Re publishes each flagship sigma
    as a public PDF. The report *pages* (Cloudflare challenge) and the monthly sigma explorer (login) are
    NOT scraped, and nothing here tries to get around either.
  * The PDF is downloaded once per source and split into clean prose sentences (sidebar callouts removed).
    The local model only CHOOSES which sentences to quote; it never writes text, so every finding is a
    verbatim sentence from the report. (An earlier paraphrasing version mis-paired two figures.)
  * Weekly, Swiss Re's public listing page is checked for a newer flagship report; if one exists the run
    says so (the pinned report keeps being used until sigma_source.json is updated).
  * Never raises. If anything fails the Director is told the report is unavailable and must not cite it.
"""
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import time

import requests

from . import llm
from .config import DATA_DIR

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_FILE = os.path.join(HERE, "sigma_source.json")
CACHE_FILE = os.path.join(DATA_DIR, "sigma_cache.json")
PDF_FILE = os.path.join(DATA_DIR, "sigma_current.pdf")
LISTING_URL = "https://www.swissre.com/institute/research/sigma-research.html"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
LISTING_CHECK_EVERY_S = 7 * 24 * 3600
MIN_FACTS = 4


def _read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _download_pdf(url, dest):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=90)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF") or len(r.content) < 200_000:
        raise ValueError(f"not a usable PDF ({len(r.content)} bytes)")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(r.content)
    return hashlib.sha256(r.content).hexdigest()


PDFTOTEXT = shutil.which("pdftotext") or "/opt/homebrew/bin/pdftotext"

# Topics agents selling home/auto protection to US high-net-worth clients care about.
RELEVANCE = ("premium", "pricing", "price", "rate", "inflation", "homeowner", "motor", "auto", "personal lines",
             "catastroph", "profitab", "combined ratio", "reinsurance", "soft market", "us ", "united states",
             "interest rate", "yield", "claims", "geopolit", "supply", "capacity", "cycle", "growth")
_BAD_START = re.compile(r"^(This|It|These|They|Those|Such|However|But|And|Yet|That|Its|Their|As a result|In addition)\b")
_BAD_CONTENT = re.compile(r"Figure \d|Table \d|sigma explorer|Source:|©|Swiss Re Institute sigma|\bwww\.|https?:")
# Extraction artifacts: a heading/sidebar glued into a sentence ("growth We expect", ", The recent"),
# words fused with digits ("2021and"), footnote markers ("2025.22."), or an unfinished sentence.
_ARTIFACT = re.compile(r"(?:[a-z0-9]|,) (?:We|The|In|Our|Insurance|Non-life|Life|Pricing|Property|Overall) [a-z]"
                       r"|\d[a-z]{2,}|[a-z]\d|\d,\d{1,2} [a-z]|\.\d{1,2}\.$|:\s+[A-Z][a-z]+ [a-z]+ [a-z]+.* (?:We|The) [a-z]")


def _page_prose(page):
    """One PDF page -> body text only. Two-column pages put sidebar callouts left of the body, so drop any
    text that starts left of the page's dominant body column."""
    lines = page.splitlines()
    starts = [len(l) - len(l.lstrip()) for l in lines if len(l.strip()) > 60]
    body_col = statistics.mode(starts) if starts else 0
    out = []
    for l in lines:
        segs = [(m.start(), m.group()) for m in re.finditer(r"\S+(?:[ ]{1,2}\S+)*", l)]
        out.append(" ".join(seg for start, seg in segs if start >= body_col - 3))
    return "\n".join(out)


def _sentences(pdf_path):
    """Clean, self-contained prose sentences from the report, in document order."""
    raw = subprocess.run([PDFTOTEXT, "-layout", "-f", "2", pdf_path, "-"], capture_output=True, text=True, timeout=120)
    if raw.returncode != 0 or len(raw.stdout) < 5000:
        raise RuntimeError("pdftotext failed")
    found, seen = [], set()
    for page in raw.stdout.split("\f"):
        for para in re.split(r"\n\s*\n", _page_prose(page)):
            para = re.sub(r"(\w)-\n(\w)", r"\1\2", para)
            para = re.sub(r"\s+", " ", para).strip()
            for sent in re.split(r"(?<=[a-z0-9%)])\.\s+(?=[A-Z(])", para):
                sent = sent.strip()
                if not sent.endswith("."):
                    sent += "." if sent and sent[-1].isalnum() else ""
                words = sent.split()
                if not 9 <= len(words) <= 45 or sent in seen:
                    continue
                alpha = sum(1 for w in words if re.search(r"[A-Za-z]", w)) / len(words)
                if (alpha < 0.8 or _BAD_START.match(sent) or _BAD_CONTENT.search(sent) or _ARTIFACT.search(sent)
                        or not sent[0].isupper() or not sent.endswith(".")):
                    continue
                seen.add(sent)
                found.append(sent)
    return found


def _score(sent):
    low = sent.lower()
    return sum(1 for k in RELEVANCE if k in low) + (1 if re.search(r"\d", low) else 0)


def _pick_findings(candidates, src, n=8):
    """The model may only CHOOSE which report sentences to quote; it cannot write or alter any text."""
    ranked = sorted(range(len(candidates)), key=lambda i: -_score(candidates[i]))[:70]
    ranked.sort()  # back to document order
    listing = "\n".join(f"[{i}] {candidates[i]}" for i in ranked)
    prompt = f"""These are numbered sentences taken verbatim from Swiss Re Institute's "{src['title']}" ({src['published']}).
Choose the {n} sentences most useful for agents selling home and auto protection to high-net-worth US clients.
Cover different topics: premium growth, pricing outlook (US homeowners and motor), profitability, inflation and
rates, catastrophe and geopolitical risk. Prefer sentences that stand alone and contain a specific figure.
Do not choose two sentences that say the same thing.

Return JSON only: {{"picks": [numbers]}}

{listing}"""
    picks = []
    try:
        r = llm.chat(messages=[{"role": "user", "content": prompt}], format="json", options={"temperature": 0.1})
        picks = [int(i) for i in json.loads(r["message"]["content"]).get("picks", []) if int(i) in ranked]
    except Exception as e:
        print(f"⚠️ Model pick failed ({e}); using top-scored sentences.")
    picks = list(dict.fromkeys(picks))[:n]
    if len(picks) < MIN_FACTS:
        picks = sorted(ranked, key=lambda i: -_score(candidates[i]))[:n]
    return [candidates[i] for i in sorted(picks)]


def _newest_flagship(listing_html):
    keys = {}
    for m in re.finditer(r'href="([^"]*/sigma-research/sigma-(\d{4})-(\d{2})-[^"/]*\.html)"', listing_html):
        keys[(int(m.group(2)), int(m.group(3)))] = m.group(1)
    if not keys:
        return None, None
    k = max(keys)
    url = keys[k]
    return k, ("https://www.swissre.com" + url if url.startswith("/") else url)


def _key_of(url):
    m = re.search(r"/sigma-(\d{4})-(\d{2})-", url or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _check_newer(src, cache):
    """Weekly look at Swiss Re's public listing page. Returns None or {'url','key'} of a newer flagship."""
    if time.time() - cache.get("listing_checked_at", 0) < LISTING_CHECK_EVERY_S:
        return cache.get("newer")
    newer = cache.get("newer")
    try:
        r = requests.get(LISTING_URL, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        key, url = _newest_flagship(r.text)
        mine = _key_of(src["page_url"])
        newer = {"url": url, "key": list(key)} if key and mine and key > mine else None
        cache["listing_checked_at"] = time.time()
        cache["newer"] = newer
    except Exception as e:
        print(f"⚠️ Swiss Re listing check failed: {e}")
    return newer


def get_sigma_context():
    """Returns {ok, note, label, short, title, published, url, findings, newer}. Never raises."""
    src = _read_json(SOURCE_FILE, {})
    base = {"ok": False, "note": "", "label": src.get("label"), "short": src.get("short"),
            "title": src.get("title"), "published": src.get("published"), "url": src.get("page_url"),
            "findings": [], "newer": None}
    try:
        cache = _read_json(CACHE_FILE, {})
        if cache.get("source_id") != src.get("id") or len(cache.get("findings", [])) < MIN_FACTS:
            print(f"📄 Downloading {src['label']}...")
            sha = _download_pdf(src["pdf_url"], PDF_FILE)
            candidates = _sentences(PDF_FILE)
            findings = _pick_findings(candidates, src)
            print(f"   {len(candidates)} candidate sentences, kept {len(findings)} verbatim findings")
            if len(findings) < MIN_FACTS:
                base["note"] = f"only {len(findings)} usable findings"
                return base
            cache = {"source_id": src["id"], "pdf_sha256": sha, "read_at": time.time(),
                     "candidates": len(candidates), "findings": findings}
            _write_json(CACHE_FILE, cache)
        base.update(ok=True, findings=cache["findings"])
        base["newer"] = _check_newer(src, cache)
        _write_json(CACHE_FILE, cache)
        return base
    except Exception as e:
        base["note"] = f"{type(e).__name__}: {str(e)[:120]}"
        print(f"⚠️ Swiss Re report unavailable: {base['note']}")
        return base


def format_for_prompt(sigma):
    """Text block for the Director's prompt."""
    if not sigma.get("ok"):
        return "(The Swiss Re report could not be read this run. Do NOT cite Swiss Re or any report figures.)"
    lines = "\n".join(f"- {f}" for f in sigma["findings"])
    return (f'{sigma["label"]}, "{sigma["title"]}" ({sigma["published"]}). Findings quoted from the report:\n{lines}')
