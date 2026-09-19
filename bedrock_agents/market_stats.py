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
