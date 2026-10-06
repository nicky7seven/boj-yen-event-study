"""
How do the yen and JGBs react to Bank of Japan rate hikes?
Step 1 - event study around every hike since March 2024.

Outputs (written next to this script)
  results/boj_event_study.csv    full-precision results table
  results/boj_event_study.xlsx   same table for Excel (needs openpyxl)
  results/boj_day_moves.png      chart for the research note
  data/                          cached raw prices, so results are reproducible offline

Sign conventions
  USD/JPY is yen per dollar. POSITIVE % = YEN WEAKER.
  JGB 10y change is in basis points. POSITIVE bp = yields UP (bond prices down).
"""
from io import StringIO
from pathlib import Path
import urllib.request

import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "results"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

START = "2023-10-01"   # extra history before the first hike for the volatility baseline
REFRESH = True         # set False to rerun from the cached CSVs in data/

# ---- Events ----------------------------------------------------------------
# BoJ hikes since normalisation began. Check each against boj.or.jp.
hikes = pd.DataFrame(
    [
        ("2024-03-19", "Ended negative rates", -0.10, 0.00),  # -0.1% to a 0-0.1% range, ~10bp
        ("2024-07-31", "0.1% to 0.25%", 0.10, 0.25),
        ("2025-01-24", "0.25% to 0.5%", 0.25, 0.50),
        ("2025-12-19", "0.5% to 0.75%", 0.50, 0.75),
        ("2026-06-16", "0.75% to 1.0%", 0.75, 1.00),
        ("2026-09-18", "1.0% to 1.25%", 1.00, 1.25),
    ],
    columns=["Date", "Decision", "Rate before", "Rate after"],
)
hikes["Date"] = pd.to_datetime(hikes["Date"])


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


# ---- Data: 10y JGB yield from Japan's Ministry of Finance ------------------
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


def parse_mof_csv(text: str) -> pd.Series:
    lines = text.splitlines()
    header = next(i for i, l in enumerate(lines) if l.strip().lower().startswith("date"))
    df = pd.read_csv(StringIO("\n".join(lines[header:])), na_values=["-", ""],
                     on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]
    s = pd.to_numeric(df["10Y"], errors="coerce")
    s.index = df[df.columns[0]].map(parse_mof_date)
    s = s[s.index.notna()].dropna()  # keep only real dated rows with a 10y yield
    if s.empty:
        raise ValueError("Couldn't read any 10y yields from the MoF file, paste its first lines to debug")
    return s


def load_jgb10y() -> pd.Series:
    cache = DATA / "jgb10y.csv"
    if REFRESH or not cache.exists():
        parts = []
        for url in MOF_URLS:
            with urllib.request.urlopen(url, timeout=30) as r:
                parts.append(parse_mof_csv(r.read().decode("latin-1")))
        s = pd.concat(parts).sort_index()
        s = s[~s.index.duplicated(keep="last")]
        s = s[s.index >= START]
        s.rename("JGB10Y").to_csv(cache, index_label="Date")
    return pd.read_csv(cache, index_col="Date", parse_dates=True)["JGB10Y"]


# ---- Event-window maths ----------------------------------------------------
def event_window(s: pd.Series, d: pd.Timestamp, kind: str) -> dict:
    """
    Moves around decision day d, using the series' OWN trading days
    (JGBs skip Japanese holidays, FX doesn't).
      day     t-1 -> t      the reaction
      5d      t-1 -> t+4    reaction plus the following week
      follow  t   -> t+4    what happened after day 0 only
    kind="pct" gives % changes (FX), kind="bp" gives basis-point changes (yields).
    """
    if d not in s.index:
        raise ValueError(f"{s.name}: no data on {d.date()}, check before trusting this row")
    i = s.index.get_loc(d)
    if i < 1 or i + 4 >= len(s):
        raise ValueError(f"{s.name}: not enough data around {d.date()} for a 5-day window")

    before, day0, day4 = s.iloc[i - 1], s.iloc[i], s.iloc[i + 4]
    if kind == "pct":
        chg = lambda a, b: (b / a - 1) * 100
        typical = (s.pct_change() * 100).rolling(20).std().shift(1).loc[d]
    else:
        chg = lambda a, b: (b - a) * 100   # yields are in %, so x100 gives bp
        typical = (s.diff() * 100).rolling(20).std().shift(1).loc[d]

    day = chg(before, day0)
    return {
        "day": day,
        "5d": chg(before, day4),
        "follow": chg(day0, day4),
        "z": day / typical,                 # day move in units of normal daily vol
        "window_end": s.index[i + 4].date(),
    }


# ---- Run ----------------------------------------------------------------------
usdjpy = load_usdjpy()
jgb = load_jgb10y()

rows = []
for _, h in hikes.iterrows():
    d = h["Date"]
    fx = event_window(usdjpy, d, "pct")
    bond = event_window(jgb, d, "bp")
    rows.append({
        "Date": d.date(),
        "Decision": h["Decision"],
        "Hike (bp)": round((h["Rate after"] - h["Rate before"]) * 100),
        "USDJPY day %": fx["day"],
        "USDJPY 5d %": fx["5d"],
        "USDJPY follow %": fx["follow"],
        "USDJPY day z": fx["z"],
        "JGB10y day bp": bond["day"],
        "JGB10y 5d bp": bond["5d"],
        "JGB10y follow bp": bond["follow"],
        "JGB10y day z": bond["z"],
        "JGB window ends": bond["window_end"],
    })

results = pd.DataFrame(rows)
results["Yen on the day"] = results["USDJPY day %"].map(lambda x: "weaker" if x > 0 else "stronger")

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
print(results.round(2).to_string(index=False))

results.to_csv(OUT / "boj_event_study.csv", index=False)
try:
    results.to_excel(OUT / "boj_event_study.xlsx", index=False)
except ImportError:
    print("openpyxl not installed, skipped Excel export (pip install openpyxl)")


# ---- Chart ------------------------------------------------------------------
# Two panels rather than one chart with two y-axes, because % and bp aren't comparable.
INK, MUTED, GRID, BAR = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
labels = [pd.Timestamp(d).strftime("%b %Y") for d in results["Date"]]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
panels = [
    (axes[0], "USDJPY day %", "USD/JPY on decision day (%)", "Above zero = yen weaker", "{:+.2f}%"),
    (axes[1], "JGB10y day bp", "10y JGB yield on decision day (bp)", "Above zero = yields higher", "{:+.1f}"),
]
for ax, col, title, note, fmt in panels:
    vals = results[col]
    bars = ax.bar(labels, vals, color=BAR, width=0.55, zorder=2)
    ax.axhline(0, color=MUTED, linewidth=1, zorder=3)
    pad = (vals.abs().max() or 1) * 0.06
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + (pad if v >= 0 else -pad), fmt.format(v),
                ha="center", va="bottom" if v >= 0 else "top", fontsize=9, color=INK)
    lim = vals.abs().max() * 1.3 or 1
    ax.set_ylim(-lim, lim)
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold", pad=22)
    ax.text(0, 1.025, note, transform=ax.transAxes, fontsize=8.5, color=MUTED, va="bottom")
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)

fig.suptitle("Market reaction to each Bank of Japan rate hike since March 2024",
             x=0.01, ha="left", fontsize=13, color=INK, fontweight="bold")
fx_src = "Federal Reserve H.10 (USD/JPY, noon New York)" if FX_SOURCE == "fred" else "Yahoo Finance (USD/JPY)"
fig.text(0.01, 0.01, f"Sources: {fx_src}, Japan Ministry of Finance (10y JGB, Tokyo close). "
         "Move = decision day vs previous day.", fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 0.93))
fig.savefig(OUT / "boj_day_moves.png", dpi=200)
print(f"\nSaved results and chart to {OUT}")
