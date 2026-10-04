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

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not configured. Add it as a GitHub Actions repository secret.")

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
            freshness = {}
            market_keys = ["nifty_previous_close","sensex_previous_close","gift_nifty","us_markets","asian_markets","brent_crude","gold","usd_inr","us_10y"]

            def missing_metric(value):
                if value is None:
                    return True
                text = str(value).strip().lower()
                return (not text) or any(marker in text for marker in [
                    "not available", "unavailable", "no data", "n/a",
                    "markets closed", "market closed", "data unavailable"
                ])

            for key in market_keys:
                if missing_metric(dashboard.get(key)):
                    old_value = previous_dashboard.get(key)
                    if not missing_metric(old_value):
                        dashboard[key] = old_value
                        freshness[key] = {
                            "status": "last_recorded",
                            "recorded_edition": previous.get("edition_date") or previous.get("edition_title") or "previous edition"
                        }
                    else:
                        dashboard[key] = "Not available from today's source set"
                        freshness[key] = {"status": "unavailable"}
                else:
                    freshness[key] = {"status": "current"}
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
                    sources[key] = old_source if isinstance(old_source, dict) else fallback
                else:
                    value.setdefault("source", fallback["source"])
                    value.setdefault("url", fallback["url"])
                if freshness.get(key, {}).get("status") == "last_recorded":
                    old_source = previous_sources.get(key)
                    if isinstance(old_source, dict):
                        sources[key] = {
                            "source": old_source.get("source") or fallback["source"],
                            "url": old_source.get("url") or fallback["url"]
                        }
            dashboard["dashboard_sources"] = sources
            dashboard["dashboard_freshness"] = freshness
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