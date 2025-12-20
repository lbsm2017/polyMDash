**Python-based real-time dashboard**, including market discovery, trades, and leaderboards. Below is a **precise technical foundation** to proceed with the project:

---

# 1. **API Layers Relevant for Your Dashboard**

## **A. Polymarket *Gamma API* — Core Market Data (REST)**

This is the **primary public read-only API** for retrieving markets, events, and metadata. It’s suitable for fetching:

* All markets and filtering by active/closed status
* Market conditions and outcomes (prices/probabilities)
* Event groupings of markets
* Tags/categories for filtering hot topics

**Base URL:**

```
https://gamma-api.polymarket.com
```

**Typical Endpoints:**

* `GET /markets` — list markets (filterable and paginated)
* `GET /markets/{id}` — market by ID
* `GET /markets/slug/{slug}` — market by slug
* `GET /events` — lists events, each containing metadata and associated markets
* `GET /tags` — tag/categorical metadata for market filtering
  **Characteristics:**
* Publicly accessible (no API key required for read-only)
* Paginated (limit/offset)
* Rich metadata including liquidity, volume, outcomes, prices, category, etc. ([Polymarket][1])

This API will be the backbone for fetching **hot markets and odds**.

---

## **B. Polymarket *Data-API* — Trades and Activities (REST)**

While the Gamma API handles market metadata, the **Data-API** provides **user activity and trade history**, which is essential for your leaderboards.

**Base URL:**

```
https://data-api.polymarket.com
```

**Key Endpoint for You:**

```
GET /trades
```

Retrieves **recent trades across markets and traders**, ordered by timestamp (descending).
Supports optional filters such as:

* `limit` — number of records
* `offset` — pagination
* `takerOnly=true/false` — filter buy/sell side
* `user` — address filter
* `market` or `eventId` — restrict to specific markets/events

**Response includes**:

* Proxy wallet address (user)
* Side (BUY/SELL)
* Market slug / event slug
* Outcome
* Price and size
* Timestamp
* Display metadata like name/pseudonym/profile image
  **Use Case:** You can use this to track **trade activity by users** for leaderboards and watchlists. ([Polymarket][2])

---

## **C. Realtime Data Socket (RTDS) — Live Updates (WebSocket)**

For **live activity streams**, you’ll use the WebSocket endpoint:

```
wss://ws-live-data.polymarket.com
```

This feeds **real-time price ticks, volume updates, and activity** without needing repeated polling; ideal for 15-second dashboard refreshes.
Data delivered includes:

* Price updates per outcome
* Volume events
* Comments or live chat data (if needed)
* Other market dynamic fields ([Polymarket][3])

---

# 2. **Data Structures You Will Leverage**

Here are the critical datasets your dashboard needs:

### **Markets**

From Gamma API (`/markets`):

* `id`, `question`, `slug`, `category`
* `active`, `closed`, `endDate`
* `outcomes` and `outcomePrices`
* `liquidity`, `volume`

### **Trade Activity**

From Data-API (`/trades`):

* `proxyWallet` (user identifier)
* `side`, `price`, `size`
* `timestamp`
* `slug` (market identifier)
* `eventSlug`

### **Leaderboards**

Computed from Data-API:

* Aggregate volume
* Count of trades per user
* Profit/loss (if calculable from price history)
* Most active user ranking

---

# 3. **Python Tooling and SDKs**

Instead of raw HTTP calls, there are **community SDKs** that simplify Gamma API access:

### **Python SDK — `polymarket-gamma`**

You can install:

```
pip install polymarket-gamma
```

**Features:**

* Async-first with sync wrappers
* Pagination helpers
* Pydantic models for markets, tags, etc.
* Built-in error handling and retries

**Example Usage:**

```python
from py_gamma import GammaClient

async def fetch_markets():
    async with GammaClient() as client:
        markets = await client.markets.get_markets(limit=50, active=True)
        for m in markets:
            print(m.question, m.outcome_prices)
```

SDK supports sync and async usage, which fits well with a **Streamlit dashboard backend**. ([PyPI][4])

---

# 4. **Proposed Dashboard Architecture (High Level)**

### **Backend**

* Python | Async where appropriate
* Polymarket Data Fetcher Modules:

  * `gamma_client.py` — market discovery & filtering
  * `trades_client.py` — trade history for leaderboards
  * `realtime_ws.py` — WebSocket client for RTDS

### **Data Layer**

* In-memory cache (e.g., Redis) or persistent store (SQLite/Postgres)
* Tasks:

  * Store user trade activity
  * Compute user leaderboard scores
  * Track hot markets (top volume, price moves)

### **Refresh Strategy**

* **REST polling** every 15 seconds for markets and trades (fallback)
* **Realtime WS** for price and volume updates

### **Frontend — Streamlit**

Key dashboard screens:

1. **Leaderboard View**

   * Top traders by volume
   * Filters by time window (last 15 min, 24h, etc.)
2. **Watchlist Viewer**

   * Selected markets with live odds (prices)
   * Signal indicators (volatility / volume spikes)
3. **Hot Markets Survey**

   * Quick filter by tag/category
   * Volume and liquidity trends
4. **Realtime Data Panel**

   * Price movements
   * Recent trades feed

---

# 5. **Next Technical Steps**

Here’s what we will focus on next:

1. **Define Python client modules**

   * REST wrappers for markets and trades
   * Async WebSocket handler for live updates
2. **Design Database Schema**

   * Users table (tracked by wallet)
   * Trades table
   * Markets table
   * Leaderboard computations
3. **Set up a Streamlit project skeleton**

   * Refresh intervals
   * Cached state management
4. **Implement simple prototype screens**

   * Basic leaderboard
   * Live watchlist chart

---

If you want, I can now **draft the Python modules** (REST + WS clients) with async support and caching logic that you can integrate into your Streamlit app.

[1]: https://docs.polymarket.com/developers/gamma-markets-api/overview?utm_source=chatgpt.com "Overview - Polymarket Documentation"
[2]: https://docs.polymarket.com/developers/CLOB/trades/trades-data-api?utm_source=chatgpt.com "Get Trades (Data-API) - Polymarket Documentation"
[3]: https://docs.polymarket.com/quickstart/introduction/endpoints?utm_source=chatgpt.com "Endpoints - Polymarket Documentation"
[4]: https://pypi.org/project/polymarket-gamma/?utm_source=chatgpt.com "polymarket-gamma · PyPI"
