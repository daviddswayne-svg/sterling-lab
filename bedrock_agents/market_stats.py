"""Deterministic values for the Bedrock page's market tiles.

Everything here is computed from real fetched data. If an input is missing the tile shows "—";
nothing is ever guessed or left to the language model.
"""

MISSING = "—"


def _vix_label(v):
    return "LOW" if v < 16 else "MODERATE" if v < 25 else "HIGH"


def compute_market_stats(raw, macro):
    raw = raw or {}
    macro = macro or {}
    out = {k: MISSING for k in ("market_sp500", "market_volatility", "market_yield", "market_inflation", "market_sector")}

    spy, vix, tnx, kie = raw.get("SPY"), raw.get("^VIX"), raw.get("^TNX"), raw.get("KIE")
    if spy:
        out["market_sp500"] = f"{spy['change_pct']:+.2f}% ${spy['price']:,.2f}"
    if vix:
        out["market_volatility"] = f"{vix['price']:.1f} ({_vix_label(vix['price'])})"
    if tnx:
        out["market_yield"] = f"{tnx['price']:.2f}%"
    if macro.get("cpi_yoy") is not None:
        prev = macro.get("cpi_yoy_prev")
        arrow = "" if prev is None else " ▲" if macro["cpi_yoy"] > prev else " ▼" if macro["cpi_yoy"] < prev else " ▬"
        out["market_inflation"] = f"{macro['cpi_yoy']:+.1f}%{arrow}"
    if kie and spy:
        rel = kie["return_1m_pct"] - spy["return_1m_pct"]  # insurers vs S&P over one month
        out["market_sector"] = "POSITIVE" if rel > 0.5 else "NEGATIVE" if rel < -0.5 else "NEUTRAL"
    return out


# ---- Market snapshot table -------------------------------------------------------------------
# (display name, symbol, kind). kind: "px" = price, "vix" = index level, "yld" = yield in percent.
TABLE_ROWS = [
    ("S&P 500", "SPY", "px"),
    ("Insurance sector", "KIE", "px"),
    ("Chubb", "CB", "px"),
    ("Progressive", "PGR", "px"),
    ("Aon", "AON", "px"),
    ("VIX (volatility)", "^VIX", "vix"),
    ("10-yr Treasury yield", "^TNX", "yld"),
]


def _dir(x, neutral=False):
    if x is None or neutral:
        return "flat" if x is not None else "na"
    return "up" if x > 0.005 else "down" if x < -0.005 else "flat"


def _pct(x):
    return f"{x:+.2f}%"


def _bps(price, pct_change):
    """Change in a yield, in basis points, from its level and percentage change."""
    prev = price / (1 + pct_change / 100)
    return (price - prev) * 100


def compute_market_table(raw):
    """Rows for the Bedrock page's market snapshot. Every value is computed from fetched data;
    a missing ticker shows dashes (never a guess). Returns {"rows": [...], "as_of": "Sep 18, 2026" | None}."""
    from datetime import datetime
    raw = raw or {}
    rows, dates = [], []
    for name, sym, kind in TABLE_ROWS:
        d = raw.get(sym)
        row = {"name": name, "symbol": sym.lstrip("^"), "level": MISSING, "day": MISSING, "month": MISSING,
               "day_dir": "na", "month_dir": "na"}
        if d:
            if d.get("as_of"):
                dates.append(d["as_of"])
            if kind == "px":
                row["level"] = f"${d['price']:,.2f}"
            elif kind == "vix":
                row["level"] = f"{d['price']:.2f}"
            else:
                row["level"] = f"{d['price']:.2f}%"
            if kind == "yld":  # yields move in basis points, not percent
                day, mon = _bps(d["price"], d["change_pct"]), _bps(d["price"], d["return_1m_pct"])
                row.update(day=f"{day:+.0f} bps", month=f"{mon:+.0f} bps")
            else:
                day, mon = d["change_pct"], d["return_1m_pct"]
                row.update(day=_pct(day), month=_pct(mon))
            neutral = kind in ("vix", "yld")   # a rising VIX or yield is not "good" or "bad" by itself
            row.update(day_dir=_dir(day, neutral), month_dir=_dir(mon, neutral))
        rows.append(row)

    # The relative-performance line the old "Sector Alpha" chart was meant to show
    kie, spy = raw.get("KIE"), raw.get("SPY")
    if kie and spy:
        rel = kie["return_1m_pct"] - spy["return_1m_pct"]
        rows.append({"name": "Insurers vs S&P 500", "symbol": "1-MONTH", "level": MISSING, "day": MISSING,
                     "month": f"{rel:+.1f} pts", "day_dir": "na", "month_dir": _dir(rel)})
    as_of = None
    if dates:
        as_of = datetime.strptime(max(dates), "%Y-%m-%d").strftime("%b %-d, %Y")
    return {"rows": rows, "as_of": as_of}
