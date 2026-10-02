async function load(){
  const newspaper=document.querySelector("#newspaper");
  try{
    const r=await fetch("data/latest.json?ts="+Date.now(),{cache:"no-store"});
    if(!r.ok) throw new Error("Data request failed: "+r.status);
    const d=await r.json();
    const data=(window.__THE_CAPITAL_DATA__&&typeof window.__THE_CAPITAL_DATA__==="object")?window.__THE_CAPITAL_DATA__:d;
    document.title=data.edition_title||"THE CAPITAL";
    document.querySelector("#edition").textContent=data.edition_date||"7:00 AM IST";
    newspaper.innerHTML=dashboard(data.dashboard||{})+renderStories(data.stories||[]);
  }catch(e){
    console.error(e);
    newspaper.innerHTML="<p class='error'>Today's edition is temporarily unavailable. Please refresh in a moment.</p>";
  }
}
function dashboard(d){
  const metrics=[
    ["Nifty (prev close)",d.nifty_previous_close,"nifty_previous_close"],
    ["Sensex (prev close)",d.sensex_previous_close,"sensex_previous_close"],
    ["GIFT Nifty",d.gift_nifty,"gift_nifty"],
    ["S&P 500 / Nasdaq",d.us_markets,"us_markets"],
    ["Asia indices",d.asian_markets,"asian_markets"],
    ["Brent crude",d.brent_crude,"brent_crude"],
    ["Gold",d.gold,"gold"],
    ["USD / INR",d.usd_inr,"usd_inr"],
    ["US 10Y",d.us_10y,"us_10y"]
  ];
  const src=d.dashboard_sources||{};
  return "<section class='dashboard'><div class='eyebrow'>5-MINUTE MARKET DASHBOARD</div><div class='metrics'>"+
    metrics.map(function(m){
      const s=src[m[2]]||{};
      const url=s.url||defaultSource(m[2]);
      const label=s.source||defaultLabel(m[2]);
      return "<div class='metric'><span>"+esc(m[0])+"</span><strong>"+esc(m[1])+"</strong><a href='"+escAttr(url)+"' target='_blank' rel='noopener'>SOURCE: "+esc(label)+" →</a></div>";
    }).join("")+
    "</div><div class='dashboard-grid'><div><div class='label'>TODAY'S KEY EVENTS</div><ul>"+
    (d.key_events||[]).map(function(x){return "<li>"+esc(x)+"</li>"}).join("")+
    "</ul></div><div><div class='label'>3 THINGS THAT COULD MOVE INDIA TODAY</div><ul>"+
    (d.three_market_movers||[]).map(function(x){return "<li>"+esc(x)+"</li>"}).join("")+
    "</ul></div></div></section>";
}
function defaultLabel(k){
  return {
    gold:"All India Bullion",us_markets:"Google Finance",asian_markets:"Google Finance",
    usd_inr:"Google Finance",nifty_previous_close:"Google Finance",sensex_previous_close:"Google Finance",
    gift_nifty:"Google Finance",brent_crude:"Google Finance",us_10y:"Google Finance"
  }[k]||"Market source";
}
function defaultSource(k){
  return {
    nifty_previous_close:"https://www.google.com/finance/quote/NIFTY_50:INDEXNSE",
    sensex_previous_close:"https://www.google.com/finance/quote/SENSEX:INDEXBOM",
    gift_nifty:"https://www.google.com/finance/",
    us_markets:"https://www.google.com/finance/",
    asian_markets:"https://www.google.com/finance/",
    brent_crude:"https://www.google.com/finance/quote/BZ:NYMEX",
    gold:"https://allindiabullion.com/benchmark",
    usd_inr:"https://www.google.com/finance/quote/USD-INR",
    us_10y:"https://www.google.com/finance/"
  }[k]||"#";
}
function renderStories(stories){
  const groups={};
  stories.forEach(function(s){(groups[s.section]||(groups[s.section]=[])).push(s)});
  const order=[
    "Indian Stock Market Morning Brief","Global Markets","India Government & Regulation",
    "Macro & Geopolitics","Global Tech & Emerging Sectors","India Emerging Sectors / Funding",
    "Marketing & Business Ideas","Indian Startup Ecosystem"
  ];
  return order.filter(function(x){return groups[x]&&groups[x].length}).map(function(x){
    const list=groups[x];
    return "<section class='section'><div class='section-header'>"+esc(x)+"<span>"+list.length+" REPORTS</span></div><div class='section-grid'>"+
      list.map(story).join("")+"</div></section>";
  }).join("");
}
function story(s){
  return "<article class='story'><div class='tag'>"+esc(s.importance||"medium")+" · "+esc(s.source||"")+"</div><h2>"+esc(s.headline||"")+
    "</h2><div class='meta'>"+esc(s.published_at||"")+"</div>"+
    section("WHAT HAPPENED",s.what_happened)+section("WHY IT MATTERS",s.why_it_matters)+
    section("WHAT TO WATCH TODAY",s.what_to_watch_today)+section("MARKET / BUSINESS IMPACT",s.market_business_impact)+
    deepDive(s)+"<div class='source'><a href='"+escAttr(s.source_url||"#")+"' target='_blank' rel='noopener'>ORIGINAL SOURCE →</a></div></article>";
}
function deepDive(s){
  const modern = s.news_brief || s.business_context || s.market_context || s.editors_read;
  if(!modern){
    return section("WHAT HAPPENED",s.what_happened)+section("WHY IT MATTERS",s.why_it_matters)+section("WHAT TO WATCH TODAY",s.what_to_watch_today)+section("MARKET / BUSINESS IMPACT",s.market_business_impact);
  }
  return "<div class='deep-dive'>"+
    section("THE NEWS",s.news_brief)+
    section("THE BUSINESS",s.business_context)+
    section("THE MARKET",s.market_context)+
    section("THE EDITOR'S READ",s.editors_read)+
    "</div>";
}
function section(label,value){return "<div class='label'>"+label+"</div><p>"+esc(value)+"</p>"}
function esc(x){
  return String(x==null?"":x).replace(/[&<>"']/g,function(m){
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m];
  });
}
function escAttr(x){return esc(x).replace(/javascript:/gi,"")}
document.querySelector("#refresh").addEventListener("click",function(){load()});
load();