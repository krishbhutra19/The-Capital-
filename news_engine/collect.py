import json, hashlib, html, re, calendar
from datetime import datetime, timezone, timedelta
from pathlib import Path
import feedparser

ROOT=Path(__file__).resolve().parents[1]
sources=json.loads((ROOT/'config/sources.json').read_text())
now=datetime.now(timezone.utc); cutoff=now-timedelta(hours=18)
items=[]
def clean(s): return re.sub(r'\\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s or ''))).strip()
for feed in sources['feeds']:
    try:
        parsed=feedparser.parse(feed['url'])
        for e in parsed.entries[:40]:
            title=clean(getattr(e,'title','')); url=getattr(e,'link','')
            if not title or not url: continue
            summary=clean(getattr(e,'summary',''))
            published=getattr(e,'published_parsed',None) or getattr(e,'updated_parsed',None)
            dt=datetime.fromtimestamp(calendar.timegm(published),tz=timezone.utc) if published else now
            if dt < cutoff: continue
            items.append({'id':hashlib.sha256(url.encode()).hexdigest()[:20],'title':title,'summary':summary[:1600],'url':url,'source':feed['name'],'category':feed['category'],'published_at':dt.isoformat()})
    except Exception as exc: print(f"Feed failed: {feed['name']}: {exc}")
seen=set(); unique=[]
for x in sorted(items,key=lambda z:z['published_at'],reverse=True):
    if x['url'] in seen: continue
    seen.add(x['url']); unique.append(x)
out=ROOT/'data'/'raw_news.json'; out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'generated_at':now.isoformat(),'items':unique[:120]},ensure_ascii=False,indent=2))
print(f'Collected {len(unique[:120])} stories')
