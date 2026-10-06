"""
How do the yen and JGBs react to Bank of Japan decisions?
Event study around every BoJ policy meeting since March 2024 (hikes AND holds).

Outputs (written next to this script)
  results/boj_event_study.csv    full-precision results table
  results/boj_event_study.xlsx   same table for Excel (needs openpyxl)
  results/boj_day_moves.png      chart for the research note
  data/                          cached raw prices, so results are reproducible offline

Sign conventions
  USD/JPY is yen per dollar. POSITIVE % = YEN WEAKER.
  JGB yield changes are in basis points. POSITIVE bp = yields UP (bond prices down).
"""
from io import StringIO
from pathlib import Path
import urllib.request

import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "results"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

START = "2023-10-01"   # extra history before the first meeting for the volatility baseline
REFRESH = True         # set False to rerun from the cached CSVs in data/
PRE_DAYS = 10          # run-up window: t-1-PRE_DAYS -> t-1 (about two weeks before the meeting)

# ---- Events ----------------------------------------------------------------
# Every BoJ Monetary Policy Meeting since March 2024. Date = the decision day (second day
# of the meeting). Dates from boj.or.jp/en/mopo/mpmsche_minu/. Check decisions against
# each meeting's statement on boj.or.jp.
meetings = pd.DataFrame(
    [
        # date,        decision, change (bp), policy rate after
        ("2024-03-19", "Hike", 10, "0-0.1%"),   # ended negative rates (-0.1% -> 0-0.1%)
        ("2024-04-26", "Hold", 0, "0-0.1%"),
        ("2024-06-14", "Hold", 0, "0-0.1%"),
        ("2024-07-31", "Hike", 15, "0.25%"),
        ("2024-09-20", "Hold", 0, "0.25%"),
        ("2024-10-31", "Hold", 0, "0.25%"),
        ("2024-12-19", "Hold", 0, "0.25%"),
        ("2025-01-24", "Hike", 25, "0.5%"),
        ("2025-03-19", "Hold", 0, "0.5%"),
        ("2025-05-01", "Hold", 0, "0.5%"),
        ("2025-06-17", "Hold", 0, "0.5%"),
        ("2025-07-31", "Hold", 0, "0.5%"),
        ("2025-09-19", "Hold", 0, "0.5%"),
        ("2025-10-30", "Hold", 0, "0.5%"),
        ("2025-12-19", "Hike", 25, "0.75%"),
        ("2026-01-23", "Hold", 0, "0.75%"),
        ("2026-03-19", "Hold", 0, "0.75%"),
        ("2026-04-28", "Hold", 0, "0.75%"),
        ("2026-06-16", "Hike", 25, "1.0%"),
        ("2026-07-31", "Hold", 0, "1.0%"),
        ("2026-09-18", "Hike", 25, "1.25%"),
    ],
    columns=["Date", "Decision", "Change (bp)", "Policy rate after"],
)
meetings["Date"] = pd.to_datetime(meetings["Date"])


# ---- Data: USD/JPY ---------------------------------------------------------
# "fred"  = Federal Reserve H.10 noon New York rate (official, correctly dated). DEFAULT.
# "yahoo" = Yahoo Finance JPY=X. Kept as a cross-check. Its daily closes appeared to be
#           shifted by a day around known BoJ dates, so don't use it for the note without checking.
FX_SOURCE = "fred"


def load_usdjpy() -> pd.Series:
    print("USD/JPY source:", FX_SOURCE)
    return load_usdjpy_fred() if FX_SOURCE == "fred" else load_usdjpy_yahoo()


def load_usdjpy_fred() -> pd.Series:
    # Noon New York on day t is AFTER a BoJ announcement made around noon Tokyo on day t
    # (that's ~11pm New York on t-1), and noon NY on t-1 is BEFORE it. So t-1 -> t captures it.
    cache = DATA / "usdjpy_fred.csv"
    if REFRESH or not cache.exists():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS&cosd={START}"
        df = pd.read_csv(url, index_col=0, parse_dates=True, na_values=".")
        s = df.iloc[:, 0].dropna()
        s.rename("USDJPY").to_csv(cache, index_label="Date")
    return pd.read_csv(cache, index_col="Date", parse_dates=True)["USDJPY"]


def load_usdjpy_yahoo() -> pd.Series:
    cache = DATA / "usdjpy.csv"
    if REFRESH or not cache.exists():
        raw = yf.Ticker("JPY=X").history(start=START)
        print("Yahoo bar timezone:", raw.index.tz)
        s = raw["Close"].dropna()
        s.index = s.index.tz_localize(None).normalize()
        s = s[~s.index.duplicated(keep="last")]  # Yahoo FX sometimes repeats a day
        s = s[s.index.dayofweek < 5]             # drop stray weekend bars
        s.rename("USDJPY").to_csv(cache, index_label="Date")
    return pd.read_csv(cache, index_col="Date", parse_dates=True)["USDJPY"]


# ---- Data: JGB yields from Japan's Ministry of Finance ---------------------
# 2Y = best free read on near-term BoJ expectations. 10Y = longer-run view (plus fiscal and global factors).
MOF_URLS = [
    "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv",
    "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv",  # current month
]
ERA_START = {"S": 1925, "H": 1988, "R": 2018}  # Showa, Heisei, Reiwa (year 1 = start + 1)


def parse_mof_date(x: str) -> pd.Timestamp:
    """MoF dates come either as 2024/3/19 or in Japanese era format like R6.3.19.
    Anything else (e.g. the notes MoF puts at the bottom of the file) becomes NaT."""
    x = str(x).strip()
    try:
        if x[:1] in ERA_START and "." in x:
            y, m, d = x[1:].split(".")
            return pd.Timestamp(ERA_START[x[0]] + int(y), int(m), int(d))
        return pd.to_datetime(x, format="%Y/%m/%d")
    except (ValueError, TypeError):
        return pd.NaT


def parse_mof_csv(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    header = next(i for i, l in enumerate(lines) if l.strip().lower().startswith("date"))
    df = pd.read_csv(StringIO("\n".join(lines[header:])), na_values=["-", ""],
                     on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]
    df.index = df[df.columns[0]].map(parse_mof_date)
    df = df[df.index.notna()]
    out = df[["2Y", "10Y"]].apply(pd.to_numeric, errors="coerce")
    if out["10Y"].dropna().empty:
        raise ValueError("Couldn't read any yields from the MoF file, paste its first lines to debug")
    return out


def load_jgb() -> pd.DataFrame:
    cache = DATA / "jgb_yields.csv"
    if REFRESH or not cache.exists():
        parts = []
        for url in MOF_URLS:
            with urllib.request.urlopen(url, timeout=30) as r:
                parts.append(parse_mof_csv(r.read().decode("latin-1")))
        df = pd.concat(parts).sort_index()
        df = df[~df.index.duplicated(keep="last")]
        df = df[df.index >= START]
        df.to_csv(cache, index_label="Date")
    return pd.read_csv(cache, index_col="Date", parse_dates=True)


# ---- Event-window maths ----------------------------------------------------
def event_window(s: pd.Series, d: pd.Timestamp, kind: str) -> dict:
    """
    Moves around decision day d, using the series' OWN trading days
    (JGBs skip Japanese holidays, FX skips US holidays).
      pre     t-1-PRE_DAYS -> t-1   the run-up, as expectations build
      day     t-1 -> t              the reaction
      5d      t-1 -> t+4            reaction plus the following week
      follow  t   -> t+4            what happened after day 0 only
    kind="pct" gives % changes (FX), kind="bp" gives basis-point changes (yields).
    """
    s = s.dropna()
    if d not in s.index:
        raise ValueError(f"{s.name}: no data on {d.date()}, check before trusting this row")
    i = s.index.get_loc(d)
    if i - 1 - PRE_DAYS < 0 or i + 4 >= len(s):
        raise ValueError(f"{s.name}: not enough data around {d.date()} for the windows")

    start, before, day0, day4 = s.iloc[i - 1 - PRE_DAYS], s.iloc[i - 1], s.iloc[i], s.iloc[i + 4]
    if kind == "pct":
        chg = lambda a, b: (b / a - 1) * 100
        typical = (s.pct_change() * 100).rolling(20).std().shift(1).loc[d]
    else:
        chg = lambda a, b: (b - a) * 100   # yields are in %, so x100 gives bp
        typical = (s.diff() * 100).rolling(20).std().shift(1).loc[d]

    day = chg(before, day0)
    return {
        "pre": chg(start, before),
        "day": day,
        "5d": chg(before, day4),
        "follow": chg(day0, day4),
        "z": day / typical,                 # day move in units of normal daily vol
    }


# ---- Run ----------------------------------------------------------------------
usdjpy = load_usdjpy()
jgb = load_jgb()
jgb2, jgb10 = jgb["2Y"].rename("JGB2Y"), jgb["10Y"].rename("JGB10Y")

rows = []
for _, m in meetings.iterrows():
    d = m["Date"]
    fx = event_window(usdjpy, d, "pct")
    b2 = event_window(jgb2, d, "bp")
    b10 = event_window(jgb10, d, "bp")
    rows.append({
        "Date": d.date(),
        "Decision": m["Decision"],
        "Change (bp)": m["Change (bp)"],
        "Policy rate after": m["Policy rate after"],
        "USDJPY pre %": fx["pre"],
        "USDJPY day %": fx["day"],
        "USDJPY 5d %": fx["5d"],
        "USDJPY follow %": fx["follow"],
        "USDJPY day z": fx["z"],
        "JGB2y pre bp": b2["pre"],
        "JGB2y day bp": b2["day"],
        "JGB10y day bp": b10["day"],
        "JGB10y 5d bp": b10["5d"],
        "JGB10y follow bp": b10["follow"],
        "JGB10y day z": b10["z"],
    })

results = pd.DataFrame(rows)
results["Yen on the day"] = results["USDJPY day %"].map(lambda x: "weaker" if x > 0 else "stronger")

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
show = ["Date", "Decision", "Change (bp)", "USDJPY pre %", "USDJPY day %", "USDJPY 5d %", "USDJPY day z",
        "JGB2y pre bp", "JGB2y day bp", "JGB10y day bp", "JGB10y 5d bp", "Yen on the day"]
print(results[show].round(2).to_string(index=False))

# Hikes vs holds: how big is the typical reaction? (absolute moves, so direction doesn't cancel out)
summary = results.groupby("Decision").agg(
    meetings=("Date", "count"),
    yen_weaker_on_day=("USDJPY day %", lambda x: int((x > 0).sum())),
    avg_abs_usdjpy_day_pct=("USDJPY day %", lambda x: x.abs().mean()),
    avg_abs_usdjpy_day_z=("USDJPY day z", lambda x: x.abs().mean()),
    avg_abs_jgb10y_day_bp=("JGB10y day bp", lambda x: x.abs().mean()),
)
print("\nHikes vs holds (averages of absolute moves):")
print(summary.round(2).to_string())

results.to_csv(OUT / "boj_event_study.csv", index=False)
try:
    with pd.ExcelWriter(OUT / "boj_event_study.xlsx", engine="openpyxl") as xw:
        for name, df in (("Event study", results), ("Hikes vs holds", summary.reset_index())):
            df.to_excel(xw, index=False, sheet_name=name)
            ws = xw.sheets[name]
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(width + 2, 30)
            ws.freeze_panes = "B2"
except ImportError:
    print("openpyxl not installed, skipped Excel export (pip install openpyxl)")


# ---- Chart ------------------------------------------------------------------
# Two stacked panels (% and bp aren't comparable, so no shared axis). Hikes in blue, holds in grey.
INK, MUTED, GRID, HIKE, HOLD = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#b9b8b2"
labels = [pd.Timestamp(d).strftime("%b %y") for d in results["Date"]]
colors = [HIKE if dec == "Hike" else HOLD for dec in results["Decision"]]

fig, axes = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True)
panels = [
    (axes[0], "USDJPY day %", "USD/JPY on decision day (%)", "Above zero = yen weaker", "{:+.2f}%"),
    (axes[1], "JGB10y day bp", "10y JGB yield on decision day (bp)", "Above zero = yields higher", "{:+.1f}"),
]
for ax, col, title, note, fmt in panels:
    vals = results[col]
    bars = ax.bar(labels, vals, color=colors, width=0.6, zorder=2)
    ax.axhline(0, color=MUTED, linewidth=1, zorder=3)
    lim = vals.abs().max() * 1.35 or 1
    pad = lim * 0.04
    for b, v, dec in zip(bars, vals, results["Decision"]):
        if dec == "Hike":  # label only the hikes, so the labels don't crowd
            ax.text(b.get_x() + b.get_width() / 2, v + (pad if v >= 0 else -pad), fmt.format(v),
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=8, color=INK)
    ax.set_ylim(-lim, lim)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold", pad=20)
    ax.text(0, 1.02, note, transform=ax.transAxes, fontsize=8.5, color=MUTED, va="bottom")
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
axes[1].tick_params(axis="x", rotation=60)
axes[0].legend(handles=[Patch(color=HIKE, label="Hike"), Patch(color=HOLD, label="Hold")],
               loc="upper right", frameon=False, fontsize=9, ncol=2, bbox_to_anchor=(1, 1.22))

fig.suptitle("Market reaction to every Bank of Japan decision since March 2024",
             x=0.01, ha="left", fontsize=13, color=INK, fontweight="bold")
fx_src = "Federal Reserve H.10 (USD/JPY, noon New York)" if FX_SOURCE == "fred" else "Yahoo Finance (USD/JPY)"
fig.text(0.01, 0.01, f"Sources: {fx_src}, Japan Ministry of Finance (10y JGB, Tokyo close). "
         "Move = decision day vs previous day.", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(OUT / "boj_day_moves.png", dpi=200)
print(f"\nSaved results and chart to {OUT}")
