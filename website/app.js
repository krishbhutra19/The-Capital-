async function load(){
  const r=await fetch("../data/latest.json?"+Date.now());
  const d=await r.json();
  document.title=d.edition_title||"THE CAPITAL";
  const first=d.stories&&d.stories[0];
  document.querySelector("#edition").textContent=first?new Date(first.published_at).toLocaleString("en-IN",{dateStyle:"full",timeStyle:"short"}):"";
  const root=document.querySelector("#newspaper");
  root.innerHTML="";
  (d.stories||[]).forEach(function(s,i){
    const a=document.createElement("article"); a.className="story"+(i===0?" top":"");
    a.innerHTML="<div class=\"tag\">"+esc(s.category)+" · "+esc(s.importance)+"</div>"+
      "<h2>"+esc(s.headline)+"</h2><div class=\"meta\">"+esc(s.source)+" · "+esc(s.published_at)+"</div>"+
      section("What happened",s.what_happened)+section("Why it matters",s.why_it_matters)+
      section("Business implications",s.business_implications)+section("Capital allocation",s.capital_allocation_implications)+
      "<div class=\"source\"><a href=\""+escAttr(s.source_url)+"\" target=\"_blank\" rel=\"noopener\">READ ORIGINAL →</a></div>";
    root.appendChild(a);
  });
}
function section(label,value){return "<div class=\"label\">"+label+"</div><p>"+esc(value)+"</p>";}
function esc(x){return String(x==null?"":x).replace(/[&<>"\x27]/g,function(m){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","\x27":"&#39;"}[m]})}
function escAttr(x){return esc(x).replace(/javascript:/gi,"")}
load();
document.querySelector("#notify").addEventListener("click",function(){alert("Push notifications will be connected after Firebase is configured.")});