import json, os, re, time
from pathlib import Path
from google import genai

ROOT = Path(__file__).resolve().parents[1]
news = json.loads((ROOT / "data/raw_news.json").read_text())
prompt = (ROOT / "prompts/editor.txt").read_text()
api_key = os.environ.get("GEMINI_API_KEY")
out = ROOT / "data/latest.json"

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not configured. Add it as a GitHub Actions repository secret.")

client = genai.Client(api_key=api_key)
models = [os.environ.get("GEMINI_MODEL") or "gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
models = list(dict.fromkeys(models))
payload = json.dumps(news["items"], ensure_ascii=False)
last_error = None
for model in models:
    for attempt in range(3):
        try:
            response = client.models.generate_content(model=model, contents=prompt + "\n\nCANDIDATE ARTICLES:\n" + payload)
            raw = response.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
            raw = re.sub(r"\s*```$", "", raw)
            result = json.loads(raw)
            if not isinstance(result, dict) or not isinstance(result.get("stories"), list):
                raise ValueError("Gemini returned an invalid newspaper JSON structure.")
            dashboard = result.get("dashboard") or {}
            for key in ["nifty_previous_close","sensex_previous_close","gift_nifty","us_markets","asian_markets","brent_crude","gold","usd_inr","us_10y"]:
                dashboard.setdefault(key, "Not available from today's source set")
            dashboard.setdefault("key_events", [])
            dashboard.setdefault("three_market_movers", [])
            result["dashboard"] = dashboard
            result["edition_title"] = result.get("edition_title") or "THE CAPITAL — 7:00 AM IST"
            result["ai_enabled"] = True
            result["story_count"] = len(result["stories"])
            out.parent.mkdir(exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
            print(f"Prepared {len(result["stories"])} stories; AI enabled=True; model={model}")
            raise SystemExit(0)
        except Exception as exc:
            last_error = exc
            print(f"Gemini attempt failed: model={model}, attempt={attempt+1}, error={exc}")
            time.sleep(5 * (attempt + 1))
raise RuntimeError(f"Gemini analysis failed after retries: {last_error}")