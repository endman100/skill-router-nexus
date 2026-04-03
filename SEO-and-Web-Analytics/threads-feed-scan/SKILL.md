---
name: threads-feed-scan
description: Scan Threads feed posts from the homepage and collect candidate AI posts quickly. Use when browsing Threads via browser relay, especially when the page is dynamic and direct step-by-step DOM reads are too slow or unstable. Supports a page-injected JavaScript collector that auto-scrolls, accumulates post data into an in-page list, pauses/resumes, and lets the agent read the collected list instead of depending on every live DOM update.
---

# Threads Feed Scan

Use homepage-first scanning.

- Prefer staying on `https://www.threads.com/`.
- Avoid opening profile pages unless the user explicitly wants profile inspection.
- If richer data is needed, allow opening a single post in another tab for view-count lookup only.
- For follower count, prefer hovering the author's avatar or handle card on the homepage.

## Default workflow

1. Confirm the connected tab is the Threads homepage.
2. If the page is too dynamic for reliable live scraping, inject a page-side collector.
3. Let the collector auto-scroll and store normalized items in `window.__threadCollector.items`.
4. Periodically read `window.__threadCollector.stats()` or `items`.
5. Filter the collected items according to the user's criteria.
6. Pause or stop the collector when asked.

## When to use the page-injected collector

Use the collector when:
- the relay DOM updates lag behind visible scrolling
- repeated `snapshot` calls are too slow
- the user wants high-frequency feed scanning
- you need accumulation over time rather than one-screen inspection

## Collector interface

Create a global object named:

- `window.__threadCollector`

Expected methods/fields:

- `items`: collected normalized post objects
- `scan()`: inspect current viewport/cards and append unseen items
- `scrollStep()`: scroll downward
- `stats()`: return status summary
- `stop()`: stop timer and mark `running=false`
- `running`: boolean
- `startedAt`: timestamp
- `seen`: dedupe set

## Suggested normalized item shape

```js
{
  key,
  postLink,
  userHref,
  username,
  timeText,
  timeDesc,
  bodyText,
  likes,
  replies,
  reposts,
  shares,
  capturedAt
}
```

## Recommended extraction rules

- Prefer cards containing both:
  - interaction labels like `讚`, `回覆`, `轉發`, `分享`
  - time labels like `分鐘前`, `小時前`, `剛剛`, `大約`
- Extract post link from `a[href*="/post/"]`
- Extract username from a non-post profile link
- Parse counts including plain numbers and `萬`
- Remove obvious UI noise:
  - `首頁`, `搜尋`, `通知`, `建立`, `更多`, `發佈`
  - standalone metric labels
  - duplicated username lines
  - tab labels like `為你推薦`
- Expect false positives on the first version; iterate on card selection and body cleanup

## High-frequency mode

Use a short interval such as 1.5s–2.5s.

Recommended loop:

1. `scan()`
2. `scrollStep()`
3. repeat on interval

Keep scrolling increments moderate rather than huge to reduce missed cards.

## Pause / resume behavior

When the user says pause or stop:
- call `window.__threadCollector.stop()`
- confirm no more auto-scroll is happening

If resuming:
- either restart the interval on the existing collector
- or create a fresh collector if the page state was lost

## Practical constraints

- Threads relay pages may desync from visible browser state
- live DOM reads can lag behind the actual screen
- homepage cards may not show view counts directly
- use single-post tabs only when necessary to fetch views
- do not assume the first parse is clean; validate sample items before trusting the list

## Minimal browser-evaluate pattern

Inject with `browser act evaluate` and return whether the collector started successfully.

After waiting a few seconds, read:

```js
window.__threadCollector?.stats()
```

To inspect raw items:

```js
window.__threadCollector?.items.slice(-20)
```

To stop:

```js
window.__threadCollector?.stop()
```

## Success condition

Success means:
- the collector is running or paused intentionally
- items are accumulating without manual step-by-step reading
- the agent can read the accumulated list directly
- the user can interrupt at any time
