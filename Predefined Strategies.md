# Predefined Backtesting Strategies

This document defines the **built‑in trading strategies** that the AI agent must implement in the backtesting engine. All strategies should be implemented in two forms:

1. **Python implementation** (strategy logic engine)
2. **YAML definition** (user‑modifiable strategy parameters)

Each strategy describes:

* **Core Logic**
* **Required Inputs** (tickers, lookbacks, thresholds, cooldowns)
* **How to calculate signals**
* **Expected behavior / rules**
* **Example YAML block**

---

# **1. Laggard Rotation Strategy**

### **Goal:** Buy ETFs/stocks that are underperforming relative to others in the chosen universe.

## **Core Logic**

* Compute percent return for each asset over a defined lookback window (e.g., 5, 10, 20 days).
* Rank assets from worst → best.
* Select the bottom N assets (default 1).
* Only buy if the asset is not in a cooldown period.
* Allocate equal fractions of available cash across selections.
* Hold until next rebalance period.

## **Signals / Requirements**

* Universe: list of tickers
* Lookback period (days)
* Number of laggards to buy
* Purchase cooldown (days)
* Rebalance frequency (weekly, monthly)

## **Example YAML**

```yaml
name: laggard_rotation
lookback_days: 10
rebalance_frequency: weekly
laggard_count: 1
cooldown_days: 20
universe:
  - XLP
  - XLY
  - XLK
  - XLE
  - XLF
position_sizing: equal_weight
execution: next_open
```

---

# **2. Momentum Winner Strategy**

### **Goal:** Buy the strongest‑performing asset(s) over a recent momentum window.

## **Core Logic**

* Compute momentum = percent return over lookback period.
* Rank assets from best → worst.
* Buy top N assets.
* Rebalance periodically.
* Cooldown optional.

## **Example YAML**

```yaml
name: momentum_winner
lookback_days: 20
rebalance_frequency: monthly
winner_count: 1
cooldown_days: 0
universe:
  - SPY
  - QQQ
  - VTI
  - DIA
position_sizing: equal_weight
execution: next_open
```

---

# **3. Mixed Strategy (Buy Winners + Losers)**

### **Goal:** Buy both extremes — the top performers (momentum) and bottom performers (mean reversion).

## **Core Logic**

* Compute momentum/returns for lookback period.
* Select top N winners.
* Select bottom M laggards.
* Allocate equally across all selected assets.
* Rebalance.

## **Example YAML**

```yaml
name: mixed_winners_losers
lookback_days: 15
rebalance_frequency: weekly
winner_count: 1
laggard_count: 1
cooldown_days: 10
universe:
  - XLP
  - XLY
  - XLK
  - XLI
  - XLE
position_sizing: equal_weight
execution: next_open
```

---

# **4. RSI Oversold / Overbought Strategy**

### **Goal:** Buy assets with RSI below a threshold (oversold)

## **Core Logic**

* Compute RSI over given period (default: 14 days).
* If RSI < oversold_threshold (default 30) → BUY.
* If RSI > overbought_threshold (default 70) → SELL (optional).
* Allocate equal weight.
* Rebalance or apply signals daily.

## **Example YAML**

```yaml
name: rsi_mean_reversion
rsi_period: 14
oversold_threshold: 30
overbought_threshold: 70
rebalance_frequency: daily
universe:
  - SPY
  - AAPL
  - MSFT
  - IWM
position_sizing: equal_weight
execution: next_open
```

---

# **5. Buy and Hold (Baseline Strategy)**

### **Goal:** Benchmark to measure other strategies against.

## **Core Logic**

* Buy the selected assets at the start date.
* Allocate equally.
* Never rebalance.
* No signals.

## **Example YAML**

```yaml
name: buy_and_hold
universe:
  - SPY
  - QQQ
position_sizing: equal_weight
execution: first_day_only
```

---

# **6. Dollar Cost Averaging (DCA)**

### **Goal:** Invest a fixed amount at a fixed schedule.

## **Core Logic**

* At each interval (weekly/monthly), invest a fixed cash contribution.
* Spread the contribution equally across assets.
* Buy fractional shares.
* No rebalancing.

## **Example YAML**

```yaml
name: dca
contribution_amount: 100
contribution_frequency: weekly
universe:
  - VTI
  - VXUS
position_sizing: equal_weight
execution: next_open
```

---

# **7. Equal-Weighted Rebalance Strategy**

### **Goal:** Maintain equal weights across selected assets on a schedule.

## **Core Logic**

* Allocate equal weight across all assets.
* Rebalance on set frequency.
* Buy/sell to restore weight.

## **Example YAML**

```yaml
name: equal_weight_rebalance
rebalance_frequency: monthly
universe:
  - SPY
  - QQQ
  - IWM
position_sizing: equal_weight
execution: next_open
```

---

# **8. Relative Strength vs Benchmark Strategy**

### **Goal:** Own assets outperforming a benchmark (e.g., SPY)

## **Core Logic**

* Compute asset return over lookback window.
* Compute benchmark return.
* Buy assets whose return > benchmark return.
* Rebalance when signals change.

## **Example YAML**

```yaml
name: relative_strength
lookback_days: 20
benchmark: SPY
rebalance_frequency: weekly
universe:
  - XLK
  - XLF
  - XLE
  - XLP
position_sizing: equal_weight
execution: next_open
```

---

# **9. Market Crash / Deep Dip Strategy**

### **Goal:** Deploy cash only when markets fall by large %.

## **Core Logic**

* Monitor % drawdown from recent high.
* If drop exceeds threshold (e.g., -10%) → BUY.
* If recovery exceeds threshold (e.g., +5%) → SELL.

## **Example YAML**

```yaml
name: buy_the_dip
max_drawdown_lookback: 60
buy_threshold: -10
sell_threshold: 5
universe:
  - SPY
position_sizing: all_in_on_signal
execution: next_open
```

---

# **10. Simple Moving Average Crossover Strategy**

### **Goal:** Basic trend-following strategy.

## **Core Logic**

* Compute SMA short (e.g., 20-day)
* Compute SMA long (e.g., 50-day)
* Buy when short > long.
* Sell when short < long.

## **Example YAML**

```yaml
name: sma_crossover
short_window: 20
long_window: 50
universe:
  - SPY
position_sizing: single_asset
execution: next_open
```

---

# **Usage Notes for AI Agent**

* All YAML strategies must validate against the schema.
* Any undefined parameter should throw a clear error.
* Strategies must be pluggable: the system should load any YAML file dropped into `/strategies/`.
* Python implementations must live in a structured directory: `strategies/<strategy_name>.py`.

These predefined strategies give the user a powerful out-of-the-box experience and allow immediate comparison across common investing methods.
