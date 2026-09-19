"""Reads the CURRENT Swiss Re Institute publications for the Bedrock Director.

Before this module the Director was fed a hardcoded sentence labelled "Sigma 2025 Outlook", and the only
report on disk was a 2024 PDF: no report was ever actually read.

Sources live in swissre_sources.json (edit that file to change them):
  * kind=pdf      Swiss Re's OPEN PDF is downloaded once per source and split into clean prose sentences
                  (sidebar callouts removed). The local model only CHOOSES which sentences to quote; it never
                  writes text, so every finding is a verbatim sentence. (An earlier paraphrasing version
                  mis-paired two figures and invented a claim.)
  * kind=excerpt  A public abstract read in a normal browser session and stored verbatim with attribution.
                  Swiss Re's report pages sit behind Cloudflare and its full reports behind a login-only client
                  portal (sigma explorer); nothing here scrapes, bypasses or logs into either.
  * Weekly, Swiss Re's public listing page is checked for a newer flagship sigma or US P&C Outlook; the run
    says so, and the pinned source is only changed by editing the JSON.
  * Never raises. A failed source is reported and skipped; if none work the Director must not cite Swiss Re.
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
SOURCES_FILE = os.path.join(HERE, "swissre_sources.json")
CACHE_FILE = os.path.join(DATA_DIR, "sigma_cache.json")
LISTING_URL = "https://www.swissre.com/institute/research/sigma-research.html"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
LISTING_CHECK_EVERY_S = 7 * 24 * 3600
MIN_FACTS = 3


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


def _download_pdf(url, dest, min_bytes=200_000):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=90)
    r.raise_for_status()
    if not r.content.startswith(b"%PDF") or len(r.content) < min_bytes:
        raise ValueError(f"not a usable PDF ({len(r.content)} bytes)")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(r.content)
    return hashlib.sha256(r.content).hexdigest()


PDFTOTEXT = shutil.which("pdftotext") or "/opt/homebrew/bin/pdftotext"

# Topics agents selling home/auto protection to US high-net-worth clients care about.
RELEVANCE = ("insured loss", "storm", "wildfire", "hail", "flood", "hurricane", "rebuild", "reconstruction", "exposure",
             "premium", "pricing", "price", "rate", "inflation", "homeowner", "motor", "auto", "personal lines",
             "catastroph", "profitab", "combined ratio", "reinsurance", "soft market", "us ", "united states",
             "interest rate", "yield", "claims", "geopolit", "supply", "capacity", "cycle", "growth")
_BAD_START = re.compile(r"^(This|It|These|They|Those|Such|However|But|And|Yet|That|Its|Their|As a result|In addition)\b")
_BAD_CONTENT = re.compile(r"Figure \d|Table \d|sigma explorer|Source:|©|Swiss Re Institute sigma|\bwww\.|https?:")
# Extraction artifacts: a heading/sidebar glued into a sentence ("growth We expect", ", The recent"),
# words fused with digits ("2021and"), footnote markers ("2025.22."), or an unfinished sentence.
# Chart contamination (axis ticks / legends mixed into prose): runs of small integers ("0 1 2 3 4"), a bare
# small integer before an ordinary word ("50 tornado", "leading 40 insured"), or a fragment after a full stop
# (". and below"). Dropping a legitimate sentence is fine; publishing a garbled one is not.
_UNITS = ("percent|per|ppt|pp|billion|million|trillion|bn|years?|days?|months?|quarters?|times|cents|basis|"
          "hot|of|to|in|and|or|by|from|countries|regions|markets|largest|major|named")
_CHART_JUNK = re.compile(r"(?:\b\d{1,3}\b\s+){3,}"
                         r"|(?<![\d.,$])\b\d{1,3}\b (?!(?:" + _UNITS + r")\b)[a-z]"
                         r"|[a-z0-9)]\.\s+[a-z]"
                         r"|\s\+\s\d"              # spaced plus before a number: chart callout "+ 64%"
                         r"|\(%,|\d\s+\d{1,3}%")     # chart subtitle "(%, 1996–2025)" / adjacent figures "35 42%"
_ARTIFACT = re.compile(r"(?:[a-z0-9%]|,) (?:We|The|In|Our|Insurance|Non-life|Life|Pricing|Property|Overall|By|While|As|When|With|Although) [a-z]"
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


def _sentences(pdf_path, first_page=2):
    """Clean, self-contained prose sentences from the report, in document order."""
    raw = subprocess.run([PDFTOTEXT, "-layout", "-f", str(first_page), pdf_path, "-"], capture_output=True, text=True, timeout=120)
    if raw.returncode != 0 or len(raw.stdout) < 3000:
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
                if (alpha < 0.8 or _BAD_START.match(sent) or _BAD_CONTENT.search(sent) or _ARTIFACT.search(sent) or _CHART_JUNK.search(sent)
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


MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"), 1)}


def _newest_flagship(listing_html):
    """Newest flagship sigma (not 'sigma-insights') as ((year, month), url)."""
    keys = {}
    for m in re.finditer(r'href="([^"]*/sigma-research/sigma-(\d{4})-(\d{2})-[^"/]*\.html)"', listing_html):
        keys[(int(m.group(2)), int(m.group(3)))] = m.group(1)
    if not keys:
        return None, None
    k = max(keys)
    return k, _abs(keys[k])


def _newest_us_pc(listing_html):
    """Newest US P&C Outlook as ((year, month), url)."""
    keys = {}
    for m in re.finditer(r'href="([^"]*/Insurance-Monitoring/us-property-casualty-outlook-([a-z]+)-(\d{4})\.html)"', listing_html):
        if m.group(2) in MONTHS:
            keys[(int(m.group(3)), MONTHS[m.group(2)])] = m.group(1)
    if not keys:
        return None, None
    k = max(keys)
    return k, _abs(keys[k])


def _abs(url):
    return "https://www.swissre.com" + url if url.startswith("/") else url


def _key_of(url):
    m = re.search(r"/sigma-(\d{4})-(\d{2})-", url or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"us-property-casualty-outlook-([a-z]+)-(\d{4})", url or "")
    return (int(m.group(2)), MONTHS.get(m.group(1), 0)) if m else None


def _check_newer(sources, cache):
    """Weekly look at Swiss Re's public listing page. Returns a list of newer editions (possibly empty)."""
    if time.time() - cache.get("listing_checked_at", 0) < LISTING_CHECK_EVERY_S and "newer" in cache:
        return cache["newer"]
    newer = cache.get("newer", [])
    try:
        r = requests.get(LISTING_URL, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        finders = {"flagship": ("sigma flagship report", _newest_flagship),
                   "us-pc": ("US P&C Outlook", _newest_us_pc)}
        newer = []
        for src in sources:
            what, finder = finders.get(src.get("watch"), (None, None))
            if not finder:
                continue
            key, url = finder(r.text)
            mine = _key_of(src["page_url"])
            if key and mine and key > mine:
                newer.append({"what": what, "pinned": src["short"], "url": url})
        cache["listing_checked_at"] = time.time()
        cache["newer"] = newer
    except Exception as e:
        print(f"⚠️ Swiss Re listing check failed: {e}")
    return newer


def _read_source(src, cache):
    """Returns the source's public info plus findings. Never raises."""
    out = {k: src.get(k) for k in ("id", "kind", "short", "label", "title", "published")}
    out.update(url=src.get("page_url"), findings=[], ok=False, note="")
    try:
        if src["kind"] == "excerpt":
            out.update(findings=list(src["findings"]), ok=True)
            return out
        entry = cache.get("sources", {}).get(src["id"], {})
        if entry.get("pdf_url") != src["pdf_url"] or len(entry.get("findings", [])) < MIN_FACTS:
            pdf = os.path.join(DATA_DIR, f"sigma_{src['id']}.pdf")
            print(f"📄 Downloading {src['label']}...")
            sha = _download_pdf(src["pdf_url"], pdf, min_bytes=100_000)
            candidates = _sentences(pdf, src.get("first_page", 2))
            findings = _pick_findings(candidates, src, src.get("n", 6))
            print(f"   {len(candidates)} candidate sentences, kept {len(findings)} verbatim findings")
            if len(findings) < MIN_FACTS:
                out["note"] = f"only {len(findings)} usable findings"
                return out
            entry = {"pdf_url": src["pdf_url"], "pdf_sha256": sha, "read_at": time.time(),
                     "candidates": len(candidates), "findings": findings}
            cache.setdefault("sources", {})[src["id"]] = entry
        out.update(findings=entry["findings"], ok=True)
    except Exception as e:
        out["note"] = f"{type(e).__name__}: {str(e)[:120]}"
        print(f"⚠️ {src.get('short')} unavailable: {out['note']}")
    return out


def get_sigma_context():
    """Returns {ok, note, sources:[{short,label,title,published,url,findings,ok,note}], newer:[...]}. Never raises."""
    result = {"ok": False, "note": "", "sources": [], "newer": []}
    try:
        sources = _read_json(SOURCES_FILE, {}).get("sources", [])
        cache = _read_json(CACHE_FILE, {})
        if "sources" not in cache:  # cache from the earlier single-source version
            cache = {"sources": {}}
        result["sources"] = [_read_source(s, cache) for s in sources]
        result["newer"] = _check_newer(sources, cache)
        _write_json(CACHE_FILE, cache)
        result["ok"] = any(s["ok"] for s in result["sources"])
        if not result["ok"]:
            result["note"] = "; ".join(f"{s['short']}: {s['note']}" for s in result["sources"] if s["note"]) or "no sources"
    except Exception as e:
        result["note"] = f"{type(e).__name__}: {str(e)[:120]}"
        print(f"⚠️ Swiss Re sources unavailable: {result['note']}")
    return result


def format_for_prompt(sigma):
    """Text block for the Director's prompt."""
    good = [s for s in (sigma.get("sources") or []) if s["ok"]]
    if not good:
        return "(No Swiss Re publication could be read this run. Do NOT cite Swiss Re or any report figures.)"
    blocks = []
    for s in good:
        lines = "\n".join(f"  - {f}" for f in s["findings"])
        blocks.append(f'{s["label"]}, "{s["title"]}" ({s["published"]}). Quoted findings:\n{lines}')
    return "\n\n".join(blocks)


def cite_names(sigma):
    return [f'{s["label"]} ({s["published"]})' for s in (sigma.get("sources") or []) if s["ok"]]
