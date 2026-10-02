import json, os, re
from pathlib import Path
from google import genai
ROOT=Path(__file__).resolve().parents[1]
news=json.loads((ROOT/'data/raw_news.json').read_text())
prompt=(ROOT/'prompts/editor.txt').read_text()
api_key=os.environ.get('GEMINI_API_KEY'); out=ROOT/'data/latest.json'
if not api_key:
    stories=[]
    for x in news['items'][:12]:
        stories.append({'headline':x['title'],'category':x['category'],'importance':'medium','what_happened':x['summary'] or 'Open the source for the available feed description.','why_it_matters':'AI analysis is not enabled yet. Add GEMINI_API_KEY to enable editorial analysis.','business_implications':'Pending AI editorial analysis.','capital_allocation_implications':'Pending AI editorial analysis.','source':x['source'],'source_url':x['url'],'published_at':x['published_at']})
    result={'edition_title':'THE CAPITAL — Feed Preview','stories':stories,'ai_enabled':False}
else:
    client=genai.Client(api_key=api_key)
    response=client.models.generate_content(model=os.environ.get('GEMINI_MODEL','gemini-3.8-flash'),contents=prompt+'\n\nCANDIDATE ARTICLES:\n'+json.dumps(news['items'],ensure_ascii=False))
    raw=re.sub(r'^```json\\s*|\\s*```$','',response.text.strip())
    result=json.loads(raw); result['ai_enabled']=True
out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(f"Prepared {len(result.get('stories',[]))} stories; AI enabled={result.get('ai_enabled')}")
