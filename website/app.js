async function load(){
  const r=await fetch("data/latest.json?"+Date.now());
  const d=await r.json();
  document.title=d.edition_title||"THE CAPITAL";
  document.querySelector("#edition").textContent=d.edition_date||"7:00 AM IST";
  const root=document.querySelector("#newspaper");
  root.innerHTML=dashboard(d.dashboard||{})+(d.stories||[]).map(function(s,i){return story(s,i)}).join("");
}
function dashboard(d){
  const metrics=[
    ["Nifty (prev close)",d.nifty_previous_close],["Sensex (prev close)",d.sensex_previous_close],
    ["GIFT Nifty",d.gift_nifty],["US markets",d.us_markets],["Asian markets",d.asian_markets],
    ["Brent crude",d.brent_crude],["Gold",d.gold],["USD/INR",d.usd_inr],["US 10Y",d.us_10y]
  ];
  return "<section class='dashboard'><div class='eyebrow'>5-MINUTE MARKET DASHBOARD</div><div class='metrics'>"+metrics.map(function(m){return "<div class='metric'><span>"+esc(m[0])+"</span><strong>"+esc(m[1])+"</strong></div>"}).join("")+"</div><div class='dashboard-grid'><div><div class='label'>TODAY'S KEY EVENTS</div><ul>"+(d.key_events||[]).map(function(x){return "<li>"+esc(x)+"</li>"}).join("")+"</ul></div><div><div class='label'>3 THINGS THAT COULD MOVE INDIA TODAY</div><ul>"+(d.three_market_movers||[]).map(function(x){return "<li>"+esc(x)+"</li>"}).join("")+"</ul></div></div></section>";
}
function story(s,i){
  return "<article class='story "+(i===0?"top":"")+"'><div class='tag'>"+esc(s.section||s.category||"")+" · "+esc(s.importance||"medium")+"</div><h2>"+esc(s.headline)+"</h2><div class='meta'>"+esc(s.source||"")+" · "+esc(s.published_at||"")+"</div>"+section("WHAT HAPPENED",s.what_happened)+section("WHY IT MATTERS",s.why_it_matters)+section("WHAT TO WATCH TODAY",s.what_to_watch_today)+section("MARKET / BUSINESS IMPACT",s.market_business_impact)+"<div class='source'><a href='"+escAttr(s.source_url)+"' target='_blank' rel='noopener'>ORIGINAL SOURCE →</a></div></article>";
}
function section(label,value){return "<div class='label'>"+label+"</div><p>"+esc(value)+"</p>"}
function esc(x){return String(x==null?"":x).replace(/[&<>"']/g,function(m){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]})}
function escAttr(x){return esc(x).replace(/javascript:/gi,"")}
load().catch(function(e){document.querySelector("#newspaper").innerHTML="<p class='error'>Edition unavailable. The 7:00 AM build may still be running.</p>"});
document.querySelector("#refresh").addEventListener("click",load);