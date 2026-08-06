# Glossary

Every abbreviation, ticker, and piece of jargon used anywhere in this repository, including on
the strategy branches. This file exists on every branch.

Nothing here assumes prior finance knowledge. If a term is used in this repo and is not defined
here, that is a bug — please open an issue.

---

## Performance metrics

| Term | Definition |
|---|---|
| **Sharpe** (Sharpe ratio) | Return per unit of volatility: annualised mean daily return divided by annualised standard deviation of daily returns. Higher is better. Computed here at a **0% risk-free rate**, so it is really "return per unit of risk versus holding cash at 0%". Roughly: below 0.5 is weak, ~1.0 is respectable, above 2.0 is exceptional (and usually too good to be true). |
| **CAGR** | Compound Annual Growth Rate — the constant yearly rate that would turn the starting balance into the ending balance. Geometric, so it accounts for compounding. A CAGR of 20% means the account multiplied by 1.20 per year on average. |
| **Vol** (volatility) | Annualised standard deviation of daily returns. A measure of how much the value bounces around. 16% is roughly a broad stock index; 90% is a 3× leveraged sector fund. |
| **Max DD** / **MaxDD** / **drawdown** | The worst peak-to-trough decline, as a percentage. A −75% max drawdown means that at some point the account was worth 25% of its previous high. This is the number that determines whether a strategy is survivable in practice. |
| **Underwater plot** | A chart of drawdown over time — how far below the previous peak the account sat on each day. Shows both the **depth** and the **duration** of losses. |
| **Growth multiple** ("Growth", "×") | Ending value per $1 invested at the start. 44× means $1 became $44. |
| **Exposure** | The share of days the strategy actually held a position rather than sitting in cash. A strategy with 2% exposure earns nothing on 98% of days. |
| **Round trip** | One complete buy-then-sell cycle. Reported here as **round trips per year**. Note this counts *cycles*, not individual orders — one round trip is two trades. |
| **MAR ratio** | CAGR divided by max drawdown. A rough "return per unit of pain" measure. |
| **rf** (risk-free rate) | The return on cash/Treasury bills, used as the baseline in a Sharpe calculation. Set to **0%** throughout this repo — see the methodology note on the main page, because it flatters strategies that stay invested and penalises those holding cash. |
| **bps** (basis points) | Hundredths of a percent. 5 bps = 0.05%. Used here for trading costs. |
| **IS** (in-sample) | The earlier period used to develop and tune a strategy. Here: 2012–2019. |
| **OOS** (out-of-sample) | The later period held back and *not* used for tuning, used to check whether a result generalises. Here: 2020–2026. A large drop from IS to OOS is the classic sign of **overfitting**. |
| **Overfitting** | Tuning a strategy so closely to historical data that it captures random noise rather than a real effect. It looks excellent in-sample and fails afterwards. |
| **t-statistic** (t-stat) | How many standard errors a measured average sits away from zero. Loosely, an absolute value above ~2 is conventionally treated as "unlikely to be chance". It assumes observations are independent — which is often false for trades, since they cluster in time. |
| **CI** (confidence interval) | A range that plausibly contains the true value. A 95% CI that excludes zero is evidence the effect is real. |
| **sd** | Standard deviation — a measure of spread around the average. |
| **Spearman correlation** | A correlation measured on *ranks* rather than values. Used here to ask whether parameters that ranked well in-sample also ranked well out-of-sample. |

---

## Indicators and strategy terms

| Term | Definition |
|---|---|
| **SMA** | Simple Moving Average — the plain average of the last *n* closing prices. `SMA(200)` is the 200-day average, a common dividing line between "uptrend" and "downtrend". |
| **EMA** | Exponential Moving Average — like an SMA but weighting recent prices more heavily, so it reacts faster. Its "span" sets how fast. |
| **RSI** | Relative Strength Index — an oscillator from 0 to 100 measuring how one-sided recent price moves have been. Below 30 is conventionally "oversold", above 70 "overbought". Uses **Wilder's smoothing** (an exponential average with α = 1/n), not a simple average. |
| **ATR** | Average True Range — a measure of how much an instrument typically moves in a day, used to size positions and set stops. Approximated in this repo by the standard deviation of daily returns. |
| **Aroon** | An indicator measuring how *recently* the highest high and lowest low occurred within a lookback window. AroonUp = 100 means today set the highest price in the window. |
| **Donchian channel** | The highest high and lowest low over the last *n* bars. A "breakout" is a close above the upper band; a "breakdown" is a close below the lower band. |
| **Trend following** | Betting that a price move will continue. Buys strength, sells weakness. |
| **Mean reversion** | Betting that a price move will reverse. Buys weakness, sells strength. The opposite assumption to trend following. |
| **Momentum (absolute / time-series)** | Comparing an instrument to its *own* past — e.g. "is the 12-month return positive?" Distinct from cross-sectional momentum, which ranks instruments against each other. |
| **Regime filter** | A rule that decides whether to be in the market at all, e.g. "only hold while price is above its 200-day average". |
| **Whipsaw** | Repeatedly being stopped out and re-entering during choppy, directionless price action, paying costs each time. |
| **Stateless vs stateful signal** | A **stateless** signal depends only on today's market (so it flips whenever a threshold is crossed). A **stateful** signal also depends on whether you currently hold a position, which lets it do nothing between an entry and an exit trigger. |
| **Look-ahead (bias)** | Accidentally using information in a backtest that was not available at the time. The most common way a backtest invents an edge that does not exist. |
| **Warm-up** | Initial bars discarded because indicators need history before they produce valid values. 252 days here. |
| **Slippage** | The difference between the price you expected and the price you got. |
| **Spread** | The gap between the buy and sell price quoted at a given moment; a cost you pay on every trade. |
| **Notional** | The dollar size of a position, as opposed to the number of shares. |
| **Position sizing** | Deciding *how much* to buy, as distinct from *when*. |
| **Time stop** | Exiting after a fixed number of bars regardless of price. |
| **Trailing stop** | An exit level that follows the price up, locking in gains but exiting on a pullback of a set size. |

---

## Instruments and markets

| Term | Definition |
|---|---|
| **ETF** | Exchange-Traded Fund — a fund that trades like a single stock. |
| **SMH** | VanEck Semiconductor ETF. Used throughout this repo as the **signal instrument** — the clean, unleveraged read on the semiconductor sector. |
| **SOXL** | Direxion Daily Semiconductor Bull 3× — the **traded instrument** here. Aims for 3× the *daily* move of a semiconductor index. |
| **SPY** | SPDR S&P 500 ETF — the standard proxy for the US stock market as a whole, and the benchmark most readers will judge everything against. |
| **S&P 500** | An index of ~500 large US companies; the default definition of "the US stock market". |
| **Russell 1000** | An index of the ~1,000 largest US companies — a broader universe than the S&P 500. |
| **B&H** | Buy and hold — the do-nothing benchmark. Buy at the start, hold to the end. |
| **Leveraged ETF / daily reset** | A fund targeting a multiple of an index's **daily** return. Because it resets each day, its long-run return is *not* the multiple of the index's long-run return. |
| **Volatility decay** | The drag a daily-reset leveraged fund suffers in choppy markets. Down 10% then up 11.1% returns an unleveraged fund to breakeven, but a 3× fund is left below it. Worse when volatility is high. |
| **Gap** | A jump between one day's close and the next day's open, with no chance to trade in between — which is why a stop cannot always protect you. |
| **Liquidity** | How easily an instrument can be traded without moving its price. |
| **Capacity** | How much money a strategy can run before its own trading erodes the edge. |

---

## Accounts and mechanics

| Term | Definition |
|---|---|
| **T+1 settlement** | Proceeds from a sale become usable cash one business day later. |
| **GFV** (Good Faith Violation) | In a cash account, buying with unsettled proceeds and selling again before settlement. Repeated violations get the account restricted — which is why **turnover matters more than trading cost** for a small cash account. |
| **PDT** (Pattern Day Trader) | A US rule restricting frequent day trading in accounts below a balance threshold. |
| **Cash account vs margin account** | A cash account can only trade settled funds; a margin account can borrow. |
| **Kill switch** | A single flag that halts all trading without needing a code change or deploy. |
| **Idempotency** | The property that running the same operation twice has the same effect as running it once — essential so a retried job cannot double-trade. |
| **Reconciliation** | Checking intended position against the broker's actual position, treating the broker as the source of truth. |
| **Dead-man's switch** | Monitoring that alerts when expected heartbeats *stop* — the only way to catch a job that never ran at all. |

---

## Data and research methodology

| Term | Definition |
|---|---|
| **Point-in-time (PIT)** | Data that reflects what was actually knowable at a given timestamp, rather than a later, revised version. Critical for any honest backtest. |
| **Survivorship bias** | Drawing conclusions from only the things that survived — delisted companies, deleted posts, closed funds — which systematically flatters results. |
| **Adjusted close** | A price series corrected for splits and dividends, so that historical prices are comparable to today's. Mandatory for instruments that have split. |
| **Walk-forward** | Repeatedly tuning on one period and testing on the next, rather than tuning once over everything. |
| **Backtest** | A simulation of a strategy over historical data. A measurement of the past under stated assumptions — never a forecast. |
| **Benchmark** | The alternative you must beat for a strategy to be worth running. Here: buy and hold. |
| **Multiple comparisons** | Testing many hypotheses and reporting the best. Some will look significant by chance, so results need correcting for how many were tried. |

---

## Sentiment / NLP terms

Used on the [`strategy/sentiment`](../../tree/strategy/sentiment) branch.

| Term | Definition |
|---|---|
| **NLP** | Natural Language Processing — computational analysis of human language. |
| **LLM** | Large Language Model — a general-purpose text model such as Claude or GPT. |
| **API** | Application Programming Interface — a defined way for programs to request data or services. |
| **Lexicon method** | Scoring text by counting words against a predefined list, with no machine learning. Fast, free, and perfectly reproducible. |
| **VADER** | A general-purpose sentiment lexicon tuned for social-media conventions. |
| **Loughran–McDonald (LM)** | A sentiment word list built specifically for **financial** text, because ordinary lexicons misread words like "liability", "cost" and "tax" as negative when they are neutral in a filing. |
| **FinBERT** | A family of small transformer models fine-tuned on financial text. |
| **Model contamination** | Scoring historical text with a model whose training data postdates it — so the model already knows what happened. An invisible form of look-ahead bias. |
| **HFT** | High-Frequency Trading — automated trading competing on microseconds, typically colocated at the exchange. |
| **Colocation** | Placing servers physically next to an exchange's systems to cut latency. |
| **Latency** | Delay between an event occurring and your system acting on it. |
| **Streaming vs batch** | **Streaming** processes data continuously as it arrives; **batch** processes it in scheduled chunks. |
| **SEC** | US Securities and Exchange Commission, the regulator that collects company filings. |
| **EDGAR** | The SEC's public filing database — free, deep, and genuinely point-in-time. |
| **10-K / 10-Q** | A company's annual / quarterly report filed with the SEC. |
| **GDELT** | A free, very large global database of news events and tone. |
| **Post-announcement drift** | The tendency of prices to keep moving in the direction of a surprise for some time after it. |

---

## Running models locally

Used on the [`strategy/sentiment`](../../tree/strategy/sentiment) and
[`research/equity-pipeline`](../../tree/research/equity-pipeline) branches.

| Term | Definition |
|---|---|
| **VRAM** | Video RAM — memory on the graphics card. This, not the GPU's speed, is what decides whether a model will run at all. |
| **Parameters** ("params", "7B") | The number of learned weights in a model, usually quoted in billions. Bigger generally means more capable and more memory-hungry. |
| **Quantisation** | Storing a model's weights at lower numeric precision (say 4 bits instead of 16) to shrink it. Costs a little accuracy and saves a lot of memory. |
| **GGUF** | A common file format for quantised models that run on CPU or GPU via llama.cpp and tools built on it. |
| **Q4_K_M** | A widely used 4-bit quantisation setting, roughly 4.5 effective bits per weight — about 0.56 GB of memory per billion parameters. |
| **KV cache** | Memory holding the model's working state for the current conversation or document. It grows with how much text the model is processing at once, and is easy to forget when budgeting VRAM. |
| **Context length** | How much text a model can consider at once. Longer context means a larger KV cache and more memory. |
| **Offloading** | Splitting a model between GPU and system RAM when it does not fit in VRAM. It works, but the part running on the CPU is much slower. |
| **Encoder model** | A model that reads text and outputs a classification or a numeric score (BERT and FinBERT are examples). Small, fast, and well suited to sentiment scoring. |
| **Generative model** | A model that writes text. Far larger for a given quality of judgement, and what "LLM" usually refers to. |
| **Embedding model** | A model that turns text into a vector of numbers so that similar passages sit near each other, enabling semantic search. Small enough to run locally with ease. |
| **Inference** | Running a trained model to get an output, as opposed to training it. |
| **Throughput** | How much work a model gets through per second — documents per second for scoring, tokens per second for generation. |
| **Ollama / llama.cpp** | Tools for running quantised models locally. llama.cpp is the underlying engine; Ollama is a friendlier wrapper around that class of tooling. |
| **ONNX Runtime** | A runtime that often makes small models meaningfully faster on CPU. |
| **vLLM** | A high-throughput serving engine aimed at large GPUs and many concurrent users — overkill for a single laptop. |
| **Pinned checkpoint** | Fixing the exact model version used, so results can be reproduced later. Hosted APIs can change the model behind a name without notice; pinning is what makes research comparable over time. |
| **CUDA** | NVIDIA's GPU compute platform, which most local-model tooling targets. |
| **ROCm** | AMD's equivalent of CUDA. Support outside Linux is considerably less mature. |

---

## Equity research terms

Used on the [`research/equity-pipeline`](../../tree/research/equity-pipeline) branch.

| Term | Definition |
|---|---|
| **Screen / screening** | Filtering a large universe of stocks down to a shortlist using quantitative criteria. |
| **z-score** | How many standard deviations a value sits from the average of its group. Used to compare companies against sector peers rather than against the whole market. |
| **Sector-relative** | Compared against companies in the same industry, so that structurally different sectors are not judged by one yardstick. |
| **Fundamentals** | Company financial data — revenue, margins, debt, cash flow — as opposed to price data. |
| **Market cap** (mktcap) | Share price × shares outstanding: the total market value of a company. |
| **ER** (expected return) | The forecast return on an investment, here built from probability-weighted scenarios. |
| **Scenario model** | Estimating several possible futures (bull / base / bear), assigning each a probability, and taking the weighted average. |
| **CAPM** | Capital Asset Pricing Model — estimates expected return as the risk-free rate plus beta × the equity risk premium. |
| **ERP** | Equity Risk Premium — the extra return investors expect from stocks over risk-free assets. |
| **Beta (β)** | How much an instrument moves relative to the overall market. Beta of 1.5 means it tends to move 1.5× as much as the market. |
| **Covariance / correlation matrix** | How instruments move together. The key input to portfolio construction — diversification comes from low correlation. |
| **Portfolio optimiser** | An algorithm choosing position weights to maximise an objective (here, Sharpe) subject to constraints. |
| **Diversification penalty** | A term in an optimiser that discourages concentrating in assets that move together. |
| **Rebalancing** | Adjusting positions back toward target weights as prices drift. |
| **IPO** | Initial Public Offering — a company's first sale of shares to the public. Recent IPOs have short price histories, which breaks correlation estimates. |
| **M&A** | Mergers and Acquisitions — which can distort a company's reported growth rates. |
| **Adversarial research** | Deliberately searching for reasons an investment thesis is *wrong*, as a check on confirmation bias. |
