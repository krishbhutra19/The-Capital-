# THE CAPITAL

Personal AI financial newspaper for Krish.

## What this project does

- Collects business and financial news from RSS feeds.
- Filters and deduplicates stories.
- Uses Gemini to select and analyze the most material stories.
- Publishes 8–12 stories per edition.
- Runs at 07:00 and 14:00 IST through GitHub Actions.
- Serves a lightweight static newspaper website.
- Supports browser push notifications through Firebase.

## Setup

1. Add GitHub Actions secrets:
   - `GEMINI_API_KEY`
   - `FIREBASE_SERVICE_ACCOUNT` (later, when push notifications are enabled)
2. Enable GitHub Pages from **Settings → Pages → GitHub Actions**.
3. Run the workflow manually once from **Actions → THE CAPITAL newspaper**.
4. Open the deployed site and enable notifications when Firebase is configured.

The first implementation deliberately avoids paid databases, paid news APIs, and web scraping.
