# How does the yen react to Bank of Japan decisions?

An event study of USD/JPY and Japanese government bond (JGB) yields around every Bank of Japan policy meeting since the end of negative interest rates in March 2024. That's 21 meetings, 6 hikes and 15 holds.

**Status** Step 1 (measuring the market reaction to every meeting) is complete. Step 2 (recording what markets expected before each meeting and the tone of each decision) is in progress, alongside a short research note with a trade idea.

## The puzzle

Higher interest rates are supposed to strengthen a currency. Yet on 18 September 2026, when the BoJ raised its policy rate 25bp to 1.25% (the highest since 1995), the yen weakened. This project asks whether that was a one-off or a pattern, and what actually moves the yen on BoJ days.

## Key findings

1. **Holds move the yen almost as much as hikes.** The average decision-day move was about 1.9 times a normal day for hikes and 1.7 times for holds. The single largest move in the sample came at a hold (April 2024, about 5.5 times a normal day). If the rate change were what mattered, holds would barely register. This supports the idea that the yen reacts to the **surprise** relative to expectations, not to the decision itself.
2. **BoJ days have mostly been bad for the yen.** The yen weakened on the day after 14 of 21 meetings, including 4 of 6 hikes and 10 of 15 holds. On average, markets came away from BoJ meetings less hawkish than they had hoped.
3. **Hikes were priced in beforehand.** The 2-year JGB yield, a proxy for expected BoJ policy, rose in the two weeks before every one of the six hikes (by about 3.4bp on average, against 1.5bp before holds). The yen also strengthened in the run-up to four of the six hikes, before giving ground on the day.
4. **Bonds respond to the decision, the yen to everything.** The 10-year JGB yield moved about twice as much on hike days (4.0bp on average) as on hold days (1.9bp). The yen moved about the same either way.
5. **Higher yields didn't reliably support the yen.** In December 2025 and June 2026 the 10-year yield rose on the day of the hike and the yen still weakened.

## Results

![Market reaction to every BoJ decision](results/boj_day_moves.png)

### Hikes vs holds

| | Meetings | Yen weaker on the day | Average USD/JPY move (size) | Size vs a normal day | Average 10y JGB move (size) |
|---|---|---|---|---|---|
| Hikes | 6 | 4 | 0.92% | 1.9x | 4.0bp |
| Holds | 15 | 10 | 0.84% | 1.7x | 1.9bp |

Averages are of the size of each move, ignoring direction, so moves up and down don't cancel out.

### Every meeting

| Decision date | Decision | USD/JPY run-up (10 days before) | USD/JPY on the day | Size vs a normal day (z) | 2y JGB run-up (bp) | 10y JGB on the day (bp) |
|---|---|---|---|---|---|---|
| **19 Mar 2024** | **Hike (ended negative rates)** | −0.87% | +1.07% | 2.7 | +1.2 | −3.0 |
| 26 Apr 2024 | Hold | +1.52% | +1.35% | 5.5 | +2.8 | +2.9 |
| 14 Jun 2024 | Hold | +0.09% | +0.33% | 0.7 | −6.7 | −3.2 |
| **31 Jul 2024** | **Hike to 0.25%** | −3.06% | −2.17% | −3.2 | +5.4 | +5.8 |
| 20 Sep 2024 | Hold | −0.38% | +0.71% | 1.2 | +1.4 | +0.9 |
| 31 Oct 2024 | Hold | +2.30% | −0.52% | −0.9 | +2.0 | −1.4 |
| 19 Dec 2024 | Hold | +2.54% | +2.42% | 3.6 | +0.4 | +1.8 |
| **24 Jan 2025** | **Hike to 0.5%** | −1.46% | −0.27% | −0.6 | +5.6 | +2.3 |
| 19 Mar 2025 | Hold | +0.46% | +0.35% | 0.7 | −1.6 | +1.3 |
| 1 May 2025 | Hold | +0.05% | +2.00% | 2.3 | +3.0 | −3.9 |
| 17 Jun 2025 | Hold | +0.97% | +0.62% | 1.0 | +0.3 | +2.1 |
| 31 Jul 2025 | Hold | +0.67% | +1.03% | 2.3 | +3.4 | −0.6 |
| 19 Sep 2025 | Hold | −0.41% | −0.13% | −0.2 | +1.8 | +4.0 |
| 30 Oct 2025 | Hold | +0.46% | +1.49% | 2.4 | +4.3 | −0.4 |
| **19 Dec 2025** | **Hike to 0.75%** | +0.41% | +1.22% | 2.9 | +5.2 | +4.9 |
| 23 Jan 2026 | Hold | +1.04% | −0.50% | −1.4 | +5.4 | +1.4 |
| 19 Mar 2026 | Hold | +1.62% | −0.81% | −2.0 | +2.6 | +4.2 |
| 28 Apr 2026 | Hold | −0.28% | +0.15% | 0.4 | −2.6 | −0.9 |
| **16 Jun 2026** | **Hike to 1.0%** | +0.34% | +0.12% | 1.0 | +0.9 | +6.6 |
| 31 Jul 2026 | Hold | −1.82% | −0.19% | −0.3 | +6.1 | 0.0 |
| **18 Sep 2026** | **Hike to 1.25%** | −1.85% | +0.65% | 1.0 | +1.8 | −1.2 |

USD/JPY is yen per dollar, so a **positive move means the yen weakened**. JGB moves are in basis points (1bp = 0.01 percentage points), and positive means yields rose. The z column divides each day's USD/JPY move by the standard deviation of daily moves over the previous 20 trading days, so values beyond about ±2 are unusually large. The full table, including 5-day moves, is in `results/boj_event_study.csv`.

## Method

- **Event windows.** For each decision day *t*, the script measures the run-up (*t−11* to *t−1*), the reaction (*t−1* to *t*), the week (*t−1* to *t+4*) and the follow-through after the first day (*t* to *t+4*).
- **Each market uses its own calendar.** JGBs don't trade on Japanese holidays and the Fed's FX series skips US holidays, so each window is counted in that market's trading days.
- **Timing.** The BoJ announces around midday Tokyo time, which is late evening of the previous day in New York. The Fed's USD/JPY rate is taken at noon New York, so the *t−1* reading comes before the announcement and the *t* reading after it. JGB yields are Tokyo closing levels, also after the announcement.
- **Expectations proxy.** The 2-year JGB yield is used as a free proxy for where markets expect BoJ policy to go. The precise measure would be overnight index swap (OIS) pricing, which isn't freely available.

## Data sources

- **USD/JPY.** Federal Reserve H.10 release via FRED (series `DEXJPUS`), noon New York buying rate.
- **JGB yields (2-year and 10-year).** Japan's Ministry of Finance daily benchmark yield files.
- **Meeting dates.** Bank of Japan monetary policy meeting schedule.

**Data check.** I first used Yahoo Finance's `JPY=X` daily closes. Compared with well-known moves, such as USD/JPY rising about 1% on 19 March 2024 and falling about 2% on 31 July 2024, the Yahoo series appeared to be shifted by one day around these events. I switched to the official Fed series, which matches those moves. The Yahoo loader remains in the script as a cross-check.

## Limitations

- **The sample is still small.** 21 meetings is enough to see patterns, not to prove them statistically.
- **Daily data mixes in other news.** In a few cases a US Federal Reserve decision was announced between the two daily readings, so part of that day's move reflects the Fed rather than the BoJ.
- **Yields trended up over the period.** Some of the rise in 2-year yields before meetings reflects that general trend. The comparison between hikes and holds matters more than the level.
- **The 10-year yield isn't set by the BoJ.** It also reflects government borrowing, inflation worries and global bond markets.

## Run it yourself

```
pip install -r requirements.txt
python bojstudy.py
```

The script writes the results table (CSV and Excel) and the chart to `results/`, and caches the raw data in `data/`. Set `REFRESH = False` to rerun from the cached data offline.

## Next steps

1. **Add meeting context.** For each meeting, record pre-meeting expectations from previews, the tone of the statement and press conference, and the vote split, then classify each as a hawkish, dovish or neutral surprise.
2. **Test the surprise hypothesis directly.** Check whether hawkish surprises line up with yen strength and dovish ones with yen weakness.
3. **Finish the research note** with a trade idea ahead of the next BoJ meeting on 29–30 October 2026.
