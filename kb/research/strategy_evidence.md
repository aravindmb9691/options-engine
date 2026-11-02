# Research-backed signals and strategies (v1, Oct 2026)

Purpose: the evidence base for `config/signals.yaml`, `engine/features/signals.py` and the selector.
The agent retrieves this file via `kb_search`. **Nothing here is enabled for live trading until it passes
`engine/backtest/gate.py` on Indian data, after costs.** Most of the evidence is from US options (1996–2019),
reported gross of costs. Indian option spreads are wider, so expect smaller or no edge.

---

## 0. Base rates: the design constraints

| Finding | Source | Implication for the engine |
|---|---|---|
| ~91% of individual F&O traders lost money in FY25; losses ₹1.05 lakh crore (+41% YoY) | SEBI FY25 study (via Moneylife) | Default answer is **no trade**; the gate must be strict |
| FY26: ~90% of pure option buyers lost; ~44% of majority-sellers lost but their average loss was much larger (~₹51.7 lakh vs ~₹1.3 lakh) | SEBI FY25–26 study, as quoted on TradingQnA | Buying = frequent small losses; selling = rare huge losses. Defined risk only. |
| Profitable in all five years FY22–26: **0.5%** of traders; loss share *rises* with experience | same | Experience is not edge; only measured expectancy counts |
| Retail losses concentrate in cheap, short-dated, OTM index options; 87% of retail notional in the last 6 days before expiry; spreads ≈ half of index-option losses | Agarwal, Ghosh, Prabhala & Zhao, *Animal Spirits on Steroids* (NSE trades 2007–2021) | No 0DTE/expiry-week lottery buying; model spreads explicitly; avoid deep OTM |
| Short-volatility on Nifty (straddles, put-writes, delta-hedged), Jan 2015–Apr 2025: **all negative after costs**; best was 6% OTM put-write at −0.9%/yr with a 91.6% win rate | Pillai (2026), SSRN 6876580 | The volatility risk premium exists but retail can't easily collect it. High win rate ≠ profit. |

---

## Tier A — volatility signals (choose *whether* to buy or sell vol on a stock)

### A1. Pre-announcement long straddle/strangle, exit before the news
- **Evidence:** Gao, Xing & Zhang, *Anticipating Uncertainty: Straddles Around Earnings Announcements*
  (JFQA; US 1996–2010). ATM straddles (moneyness 0.95–1.05, 10–60 DTE) bought 3 days before earnings and
  sold **at the announcement** earned ~3.0% (equal-weighted). Unconditional straddles lose (−2.1%/week).
  Gao, Hu & Zhang (*Uncertainty Resolution Before Earnings Announcements*): high option-implied-uncertainty
  stocks earn most of the pre-announcement premium; uncertainty falls ~1.8% in the run-up.
- **Counter-evidence for holding *through* results:** across 28,898 US reports (2023–26), the average implied
  move ±9.2% vs realized ±6.3% (≈0.69×); the close beat the implied move only 25% of the time (EarningsWatcher
  2026, vendor study). After results, ATM IV typically drops 15–40% (FlashAlpha, small samples).
- **Rule:** enter T−3 to T−2 (trading days), **exit on the last close before the announcement** by default.
  Hold through only if the stock's own **edge ratio** (median past |event move| ÷ implied move) ≥ 1.2.
- **India adaptation:** results timing (during market vs after close) comes from the NSE board-meeting notice;
  use the near-month or next-month contract with ≥10 DTE after the event; liquid strikes only.
- **This is your FY26 edge, now with a cleaner exit.**

### A2. Realized-minus-implied vol spread (Goyal & Saretto 2009, JFE)
- **Signal:** `RV_12m − IV_ATM_1m` (annualised). Long straddles in the top decile, short in the bottom
  decile, held ~1 month: ~3.9%/month long–short **after** costs in the US sample.
- **Use:** high spread ⇒ options cheap ⇒ long-vol structures allowed. Low/negative spread ⇒ options rich ⇒
  only defined-risk short vol (iron condor/fly) or no trade. Cross-sectional rank within the universe.

### A3. IV term-structure slope (Vasquez 2017, JFQA)
- **Signal:** `IV_ATM_long − IV_ATM_short` (next-month minus near-month in India). Steep upward slope ⇒ buy
  straddles; inverted ⇒ avoid buying. US 1996–2007: large gross spread; after realistic bid-ask the straddle
  long–short stays ~5–12%/month depending on the cost assumption, but becomes insignificant if effective
  spreads exceed ~1.25× quoted.
- **Note:** an inverted slope right before results is normal (event premium in the front month). Compute the
  slope **ex-event** or use it only outside event windows.

### A4. Straddle momentum (Heston, Jones, Khorram, Li & Mo, J. Finance 2021)
- **Signal:** average past monthly ATM straddle return on the stock over 6–36 months (skip the latest month;
  1-month returns tend to reverse). Pre-cost Sharpe ≥3× stock momentum; no crash risk found; **close to zero
  after paying full bid-ask** on liquid names.
- **Use:** tie-breaker/feature in the event model, not a standalone trade. We can compute it from our own
  bhavcopy history.

### Vol forecasting (inputs to A1–A3)
- HAR-RV (Corsi 2009) per stock; GARCH as benchmark.
- India evidence (Rajvanshi, Santra & Basu, IIM Calcutta WPS 797, Nifty 2011–2015): adding India VIX to
  GARCH improved forecasts; simple ARMA on realized vol forecast best. ⇒ include IV/VIX as a HAR regressor and
  always compare against a naive baseline.

---

## Tier B — direction signals (only for debit/credit spreads, half size)

| ID | Signal | Evidence | Direction | Caveat |
|---|---|---|---|---|
| B1 | **Skew/smirk** = IV(OTM put, ~0.9–0.95 moneyness) − IV(ATM call) | Xing, Zhang & Zhao 2010 JFQA: steepest smirk underperforms flattest by ~10.9%/yr risk-adjusted; predicts bad next-quarter earnings | Steep ⇒ bearish | US 1996–2005, gross; weekly rebalancing |
| B2 | **Call–put IV spread** = IV(call) − IV(put), same strike/expiry | Cremers & Weinbaum 2010 JFQA: rich calls beat rich puts by ~0.5%/week | Positive ⇒ bullish | Edge decayed over the sample; gross |
| B3 | **Stock momentum 12–1** (12-month return skipping the last month) | IIMA Indian factor library: WML ≈ 11%/yr since 1994, but −63.5% worst drawdown (2000–05) and −53% (2009) | Winners ⇒ bullish | Tilt only; crashes after market rebounds |
| B4 | **Time-series momentum** (12-month sign) on Nifty and stocks | Babu et al., *Trends Everywhere* (gross Sharpe ~1.2–1.6 across 156 assets); India: TS momentum significant, beats cross-sectional (CJFA 2020) | Trend sign | Gross; regime filter rather than signal |

---

## Tier C — tested ideas we will NOT trade (and why)

- **Naive index premium selling** (short straddles/strangles, put-writes on Nifty): negative after costs and
  tail losses in 2015–25 (Pillai 2026). Allowed only as defined-risk structures that pass the gate.
- **Holding long vol through results by default:** implied usually exceeds realized (A1 counter-evidence).
- **Post-earnings drift (PEAD) in India:** NSE evidence shows reversal, not drift (Gupta & Dhusia 2021, 100
  firms, 2014–18). Don't trade drift.
- **Delta-hedged idiosyncratic-vol trades** (Cao & Han 2013 JFE): about 1–2%/month gross, roughly zero after
  50–100% of the spread. Not viable for retail.
- **Dispersion/correlation trades** (Driessen, Maenhout & Vilkov 2009 JF): the authors state it can't be
  exploited with realistic frictions.
- **Weekly/expiry-day OTM lottery buying:** the main source of retail losses (Agarwal et al.).

---

## How the engine uses this (scrip selection → strategy)

1. **Universe:** Nifty + top ~50 F&O stocks by option turnover (point-in-time). Exclude the ban list.
2. **Liquidity filter:** bid-ask ≤ X% of premium on target strikes (from live chain; proxy from OI/volume
   in backtests), OI above threshold.
3. **Compute signals daily:** A1 edge ratio and event timing, A2 RV−IV, A3 slope (ex-event), A4 straddle
   momentum, B1–B4. Rank cross-sectionally → z-scores.
4. **Composite score:** weight signals by **out-of-sample information coefficient** from walk-forward,
   not by the paper's numbers. Start with equal weights among signals that pass a single-signal gate.
5. **Map to strategy** (SPEC §4 matrix):
   - Event ahead + A1 cheap + A2 high ⇒ long strangle/straddle, exit before the news.
   - A2 low (options rich) + no event + range regime ⇒ iron condor/fly (defined risk).
   - Direction composite (B1–B4) strong + A2 high ⇒ debit spread; + A2 low ⇒ credit spread.
   - A3 steep and ex-event ⇒ calendars considered.
   - Otherwise **no trade**.
6. **Risk engine** sizes (2.5% of capital, ₹20k cap) and the gate decides what's live.

## Validation plan per signal
- Recompute on NSE bhavcopy 2018→ with point-in-time universe; decile/quintile sorts; information coefficient
  (rank correlation with next-period straddle or stock return); walk-forward; Indian costs (STT, exchange,
  GST, stamp, brokerage, and a spread model); report gross **and** net.
- Promote only signals with a stable positive net information coefficient across sub-periods.

## Sources
- Gao, Xing & Zhang — *Anticipating Uncertainty: Straddles Around Earnings Announcements*, JFQA; summary:
  https://alphaarchitect.com/straddle-earnings-announcements-and-win/ ;
  https://resolve.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/anticipating-uncertainty-straddles-around-earnings-announcements/7B34877AD5E06304BA3C55FBA3219FDD
- Gao, Hu & Zhang — *Uncertainty Resolution Before Earnings Announcements*: https://quantpedia.com/pre-announcement-returns/
- Goyal & Saretto (2009) — *Cross-section of option returns and volatility*, JFE; overview: https://bsic.it/dislocations-historical-implied-volatility-indicators-volatility-trades/
- Vasquez (2017) — *Equity Volatility Term Structures and the Cross-Section of Option Returns*, JFQA:
  https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/equity-volatility-term-structures-and-the-cross-section-of-option-returns/F0A40E99FD2458367DD9A56A89783D38 ;
  https://www.cxoadvisory.com/volatility-effects/exploiting-the-implied-volatility-term-structure/
- Heston, Jones, Khorram, Li & Mo (2021) — *Option Momentum*, J. Finance: https://alphaarchitect.com/option-momentum/
- Cao & Han (2013) — JFE: https://www.cxoadvisory.com/volatility-effects/extracting-a-volatility-premium-with-equity-options
- Xing, Zhang & Zhao (2010) — JFQA 45(3): https://ideas.repec.org/a/cup/jfinqa/v45y2010i03p641-662_00.html
- Cremers & Weinbaum (2010) — JFQA 45(2): https://ideas.repec.org/a/cup/jfinqa/v45y2010i02p335-367_00.html
- Driessen, Maenhout & Vilkov (2009) — J. Finance 64(3): https://ideas.repec.org/a/bla/jfinan/v64y2009i3p1377-1406.html
- Pillai (2026) — *Trading the Volatility Risk Premium on Nifty 50*: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6876580
- Agarwal, Ghosh, Prabhala & Zhao — *Animal Spirits on Steroids*: https://www.ualberta.ca/en/finance-department/media-library/documents/vikas-agarwal.pdf
- SEBI FY25 study (headline): https://moneylife.in/article/91-percentage-of-retail-traders-lost-money-in-derivatives-losses-in-fo-surged-41-percentage-to-rs105-lakh-crore-in-fy25-sebi-study/77613.html
- SEBI FY25–26 findings (secondary): https://tradingqna.com/t/win-rate-capital-experience-what-sebi-found-about-f-o-traders/197266/1
- IIMA Indian Fama-French & momentum data: https://web.iima.ac.in/~iffm/Indian-Fama-French-Momentum/ ; drawdowns: https://web.iima.ac.in/~iffm/Indian-Fama-French-Momentum/drawdown.php
- Gupta & Dhusia (2021) — PEAD in NSE firms: https://journals.lib.vutbr.cz/index.php/trends/article/view/541
- Babu et al. — *Trends Everywhere*: https://quantpedia.com/time-series-momentum-works-everywhere/
- TS/CS momentum in India (CJFA 2020): https://apcz.umk.pl/CJFA/article/view/CJFA.2020.018
- Rajvanshi, Santra & Basu (2017), IIM Calcutta WPS 797: https://studentlive.iimcal.ac.in/sites/all/files/pdfs/wps_797.pdf
- EarningsWatcher (2026), implied vs actual earnings moves: https://earnings-watcher.com/wiki/options-implied-move-vs-actual-earnings-study-2026
- FlashAlpha (2026), IV crush: https://flashalpha.com/articles/how-much-does-iv-drop-after-earnings-real-crush-numbers
