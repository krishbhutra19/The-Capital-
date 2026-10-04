import json, os, re, time
from pathlib import Path
import requests
from google import genai

ROOT = Path(__file__).resolve().parents[1]
news = json.loads((ROOT / "data/raw_news.json").read_text())
prompt = (ROOT / "prompts/editor.txt").read_text()
api_key = os.environ.get("GEMINI_API_KEY")
out = ROOT / "data/latest.json"

# Fetch the last published edition so closed markets can carry forward
# their most recent valid observation (weekends and exchange holidays).
previous = {}
previous_url = os.environ.get(
    "PREVIOUS_EDITION_URL",
    "https://krishbhutra19.github.io/The-Capital-/data/latest.json"
)
try:
    previous_response = requests.get(previous_url, timeout=15, headers={"Cache-Control": "no-cache"})
    previous_response.raise_for_status()
    previous = previous_response.json()
    if not isinstance(previous, dict):
        previous = {}
except Exception as exc:
    print(f"Previous edition unavailable; using local fallback: {exc}")

if not previous and out.exists():
    try:
        previous = json.loads(out.read_text())
    except Exception:
        previous = {}

snapshot_path = ROOT / "data" / "market_snapshot.json"
last_snapshot = {}
if snapshot_path.exists():
    try:
        last_snapshot = json.loads(snapshot_path.read_text())
        if not isinstance(last_snapshot, dict):
            last_snapshot = {}
    except Exception:
        last_snapshot = {}


client = genai.Client(api_key=api_key)
models = [os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash-lite", "gemini-3.5-flash"]
models = list(dict.fromkeys(models))
payload = json.dumps(news["items"], ensure_ascii=False)
last_error = None
for model in models:
    for attempt in range(2):
        try:
            response = client.models.generate_content(model=model, contents=prompt + "\n\nCANDIDATE ARTICLES:\n" + payload)
            raw = response.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
            raw = re.sub(r"\s*```$", "", raw)
            result = json.loads(raw)
            if not isinstance(result, dict) or not isinstance(result.get("stories"), list):
                raise ValueError("Gemini returned an invalid newspaper JSON structure.")
            dashboard = result.get("dashboard") or {}
            previous_dashboard = previous.get("dashboard") or {}
            previous_sources = previous_dashboard.get("dashboard_sources") or {}
            snapshot_metrics = last_snapshot.get("metrics") or {}
            freshness = {}
            market_keys = [
                "nifty_previous_close","sensex_previous_close","gift_nifty",
                "us_markets","asian_markets","brent_crude","gold","usd_inr","us_10y"
            ]

            def missing_metric(value):
                if value is None:
                    return True
                text = str(value).strip().lower()
                return (not text) or any(marker in text for marker in [
                    "not available", "unavailable", "no data", "n/a",
                    "markets closed", "market closed", "data unavailable"
                ])

            def valid_metric(key, value):
                if missing_metric(value):
                    return False
                text = str(value).strip()
                if len(text) > 90:
                    return False
                numbers = re.findall(r"\\d[\\d,]*(?:\\.\\d+)?", text)
                if not numbers:
                    return False
                if key in {"us_markets", "asian_markets"} and len(numbers) < 2:
                    return False
                return True

            # On weekends the exchange metrics are explicitly last-recorded.
            # On weekdays, only a concise numeric market value is accepted;
            # headlines accidentally returned by the model are rejected.
            from datetime import datetime, timezone
            try:
                from zoneinfo import ZoneInfo
                india_weekday = datetime.now(ZoneInfo("Asia/Kolkata")).weekday()
            except Exception:
                india_weekday = datetime.now(timezone.utc).weekday()

            snapshot_fresh = {}
            for key in market_keys:
                current_valid = valid_metric(key, dashboard.get(key))
                if current_valid and india_weekday < 5:
                    freshness[key] = {"status": "current"}
                    snapshot_fresh[key] = {
                        "value": dashboard[key],
                        "source": (dashboard.get("dashboard_sources") or {}).get(key, {}).get("source"),
                        "url": (dashboard.get("dashboard_sources") or {}).get(key, {}).get("url"),
                        "recorded_date": result.get("edition_date") or datetime.now(timezone.utc).date().isoformat()
                    }
                    continue

                candidates = [
                    (previous_dashboard.get(key), previous_sources.get(key), "previous edition"),
                    (
                        (snapshot_metrics.get(key) or {}).get("value"),
                        snapshot_metrics.get(key),
                        (snapshot_metrics.get(key) or {}).get("recorded_date") or "last valid snapshot"
                    )
                ]
                chosen = None
                for value, source_info, recorded_label in candidates:
                    if valid_metric(key, value):
                        chosen = (value, source_info if isinstance(source_info, dict) else {}, recorded_label)
                        break

                if chosen:
                    value, source_info, recorded_label = chosen
                    dashboard[key] = value
                    freshness[key] = {
                        "status": "last_recorded",
                        "recorded_edition": recorded_label
                    }
                    if key not in snapshot_fresh:
                        snapshot_fresh[key] = {
                            "value": value,
                            "source": source_info.get("source"),
                            "url": source_info.get("url"),
                            "recorded_date": source_info.get("recorded_date") or recorded_label
                        }
                else:
                    dashboard[key] = "Not available from today's source set"
                    freshness[key] = {"status": "unavailable"}

            dashboard.setdefault("key_events", [])
            dashboard.setdefault("three_market_movers", [])
            default_sources = {
                "nifty_previous_close": {"source": "Google Finance", "url": "https://www.google.com/finance/quote/NIFTY_50:INDEXNSE"},
                "sensex_previous_close": {"source": "Google Finance", "url": "https://www.google.com/finance/quote/SENSEX:INDEXBOM"},
                "gift_nifty": {"source": "Google Finance", "url": "https://www.google.com/finance/"},
                "us_markets": {"source": "Google Finance", "url": "https://www.google.com/finance/"},
                "asian_markets": {"source": "Google Finance", "url": "https://www.google.com/finance/"},
                "brent_crude": {"source": "Google Finance", "url": "https://www.google.com/finance/quote/BZ:NYMEX"},
                "gold": {"source": "All India Bullion", "url": "https://allindiabullion.com/benchmark"},
                "usd_inr": {"source": "Google Finance", "url": "https://www.google.com/finance/quote/USD-INR"},
                "us_10y": {"source": "Google Finance", "url": "https://www.google.com/finance/"}
            }
            sources = dashboard.get("dashboard_sources") or {}
            for key, fallback in default_sources.items():
                value = sources.get(key)
                if not isinstance(value, dict):
                    old_source = previous_sources.get(key)
                    snap_source = snapshot_metrics.get(key) or {}
                    sources[key] = (
                        old_source if isinstance(old_source, dict)
                        else snap_source if isinstance(snap_source, dict) and snap_source.get("url")
                        else fallback
                    )
                else:
                    value.setdefault("source", fallback["source"])
                    value.setdefault("url", fallback["url"])
                if freshness.get(key, {}).get("status") == "last_recorded":
                    old_source = previous_sources.get(key)
                    snap_source = snapshot_metrics.get(key) or {}
                    if isinstance(old_source, dict) and old_source.get("url"):
                        sources[key] = old_source
                    elif isinstance(snap_source, dict) and snap_source.get("url"):
                        sources[key] = {
                            "source": snap_source.get("source") or fallback["source"],
                            "url": snap_source.get("url") or fallback["url"]
                        }
            dashboard["dashboard_sources"] = sources
            dashboard["dashboard_freshness"] = freshness

            # Persist only values that have passed numeric validation. The
            # workflow commits this tiny rolling snapshot back to main so a
            # weekend/holiday can never lose the last valid observation.
            if snapshot_fresh:
                last_snapshot["recorded_at"] = datetime.now(timezone.utc).isoformat()
                last_snapshot["metrics"] = snapshot_fresh
                snapshot_path.write_text(
                    json.dumps(last_snapshot, ensure_ascii=False, indent=2)
                )
            result["dashboard"] = dashboard
            result["edition_title"] = result.get("edition_title") or "THE CAPITAL — 7:00 AM IST"
            result["ai_enabled"] = True
            result["story_count"] = len(result["stories"])
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
            print(f"Prepared {len(result['stories'])} stories; AI enabled=True; model={model}")
            raise SystemExit(0)
        except Exception as exc:
            last_error = exc
            print(f"Gemini attempt failed: model={model}, attempt={attempt+1}, error={exc}")
            time.sleep(8 * (attempt + 1))
raise RuntimeError(f"Gemini analysis failed after retries: {last_error}")