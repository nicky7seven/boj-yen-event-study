# boj-yen-event-study

# How does the yen react to Bank of Japan rate hikes?

An event study of USD/JPY and 10-year JGB yields around every Bank of Japan rate hike since the end of negative rates in March 2024.

**Status** Step 1 (measuring the market reaction) is complete. Step 2 (adding market expectations and policy tone for each meeting) is in progress, followed by a research note and trade idea.

## The puzzle

On 18 September 2026 the BoJ raised its policy rate 25bp to 1.25%, the highest since 1995. The yen still weakened and 10-year JGB yields slipped on the day. Raising rates is supposed to strengthen a currency, so why didn't it?

## Results so far

![Market reaction to each BoJ hike](results/boj_day_moves.png)

| Decision date | Hike | USD/JPY on the day | USD/JPY over 5 days | 10y JGB on the day | Yen on the day |
|---|---|---|---|---|---|
| 19 Mar 2024 | Ended negative rates | +1.07% | +1.54% | −3.0bp | weaker |
| 31 Jul 2024 | 0.1% to 0.25% | −2.17% | −5.60%* | +5.8bp | stronger |
| 24 Jan 2025 | 0.25% to 0.5% | −0.27% | −1.01% | +2.3bp | stronger |
| 19 Dec 2025 | 0.5% to 0.75% | +1.22% | +0.71% | +4.9bp | weaker |
| 16 Jun 2026 | 0.75% to 1.0% | +0.12% | +0.84% | +6.6bp | weaker |
| 18 Sep 2026 | 1.0% to 1.25% | +0.65% | +1.97% | −1.2bp | weaker |

USD/JPY is yen per dollar, so a positive move means the yen weakened.
\*The July 2024 five-day window includes the weak US payrolls report and the global carry-trade unwind, so it isn't a clean BoJ effect.

**Early observations**

- The yen weakened after four of the six hikes.
- The only large yen rally (July 2024, about 3x a normal day's move) followed the hike the market had not fully priced.
- In December 2025 and June 2026, JGB yields rose and the yen still weakened, so higher Japanese yields alone haven't supported the currency.

Working hypothesis. The yen responds to the surprise relative to expectations, not to the hike itself. Step 2 tests this.

## Method

- **Event window.** For each decision day *t*, the script measures the move from *t−1* to *t* (the reaction), *t−1* to *t+4* (the week) and *t* to *t+4* (follow-through after the first day).
- **Each market uses its own calendar.** JGBs don't trade on Japanese holidays, so the bond window can span more calendar days than the FX window.
- **Size relative to normal.** Each day move is also expressed as a z-score, dividing by the standard deviation of daily moves over the previous 20 trading days.
- **Timing.** The BoJ announces around midday Tokyo time. The Fed's USD/JPY rate is taken at noon New York, which falls before the announcement on *t−1* and after it on *t*, so the day move brackets the decision.

## Data sources

- USD/JPY from the Federal Reserve H.10 release via FRED (series `DEXJPUS`), noon New York buying rate.
- 10-year JGB yields from Japan's Ministry of Finance daily benchmark yield files.

**Data check.** I first used Yahoo Finance's `JPY=X` daily closes. Compared with well-known moves (for example USD/JPY rising about 1% on 19 March 2024), the Yahoo series appeared to be shifted by one day around these events, so I switched to the official Fed series. The Yahoo loader stays in the script as a cross-check.

## Run it yourself

```
pip install -r requirements.txt
python bojstudy.py
```

The script writes the results table (CSV and Excel) and the chart to `results/`, and caches the raw data in `data/`. Set `REFRESH = False` to rerun from the cached data offline.

## Next steps

1. Add context for each meeting (pre-meeting market pricing, tone of the statement and press conference, vote split, other events in the window).
2. Extend the sample to every BoJ meeting since 2024, not just hikes.
3. Write up the findings as a short research note with a trade idea.
