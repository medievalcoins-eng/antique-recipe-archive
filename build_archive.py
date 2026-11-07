#!/usr/bin/env python3
"""Build a historical recipe archive from Fannie Merritt Farmer's 1910 original."""
import re, json, html, os, pathlib, urllib.request, urllib.parse, time
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT=pathlib.Path(__file__).resolve().parent
URL="https://www.gutenberg.org/files/65061/65061-h/65061-h.htm"
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"AntiqueRecipeArchive/1.0 (historical cookbook catalog)"})
    return urllib.request.urlopen(req,timeout=35).read()
soup=BeautifulSoup(get(URL),"html.parser")
# Gutenberg HTML headings mark each historical recipe; gather siblings until next heading.
records=[]
chapter=""
for heading in soup.find_all(re.compile("^h[2-5]$")):
    title=heading.get_text(" ",strip=True)
    if heading.name=="h2":
        chapter=re.sub(r"^CHAPTER\\s+[IVXLCDM]+\\s*","",title,flags=re.I)
        continue
    if heading.name not in ("h3","h4"):continue
    if not title or len(title)>85 or title.upper()==title or re.search(r"INDEX|GLOSSARY|CONTENTS",title,re.I):continue
    parts=[]
    # Gutenberg wraps recipe ingredient lists and instructions in different nested
    # containers. Traverse document order, not merely sibling nodes.
    for el in heading.next_elements:
        if isinstance(el,Tag) and el.name in ("h2","h3","h4","h5") and el is not heading:
            break
        if not isinstance(el,Tag):
            continue
        if el.name in ("p","table","ul","ol"):
            txt=el.get_text(" ",strip=True)
        elif el.name in ("div","li","td") and not el.find(["p","table","ul","ol","div","li","td"]):
            txt=el.get_text(" ",strip=True)
        else:
            continue
        txt=re.sub(r"\s+"," ",txt).strip()
        if txt and not re.fullmatch(r"\d{1,3}",txt) and not txt.startswith("Image") and txt not in parts[-2:]:
            parts.append(txt)
        if len(" ".join(parts))>3500:
            break
    if len(parts)<2:continue
    # Most Farmer recipes have ingredient lines in paragraph or table elements.
    if not any(re.search(r"\\b(cup|cups|tablespoon|teaspoon|pint|quart|pound|egg|flour|butter|milk|sugar|water|salt)\\b",p,re.I) for p in parts):continue
    if not any(re.search(r"\\b(mix|add|cook|bake|boil|beat|serve|stir|put|heat|wash|cream|cut|sift|strain|place|pour|fry|broil|roast|cover)\\b",p,re.I) for p in parts):continue
    key=re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")
    if not key or any(r["slug"]==key for r in records):continue
    records.append({"slug":key,"title":title,"chapter":chapter or "Historic Cookery","parts":parts[:24],"source":URL+"#"+urllib.parse.quote(heading.get("id") or (heading.find(id=True).get("id") if heading.find(id=True) else ""))})
    if len(records)>=320:break
print("Extracted",len(records),"recipes",flush=True)
if len(records)<200:raise RuntimeError(f"Extraction yielded only {len(records)} recipes; refusing to publish an incomplete archive")
# Use openly licensed Wikimedia Commons search for an illustrative food photograph.
API="https://commons.wikimedia.org/w/api.php"
def commons_image(title):
    q=re.sub(r"\\b(I|II|III|IV|V|VI|No\\.|à la|with|and)\\b"," ",title,flags=re.I)
    q=re.sub(r"[^a-zA-Z ]"," ",q).strip()
    if len(q)<4:return None
    params={"action":"query","generator":"search","gsrsearch":"filetype:bitmap "+q+" food","gsrnamespace":"6","gsrlimit":"6","prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":"800","format":"json"}
    try:
        d=json.loads(get(API+"?"+urllib.parse.urlencode(params)))
        for page in d.get("query",{}).get("pages",{}).values():
            info=page.get("imageinfo",[{}])[0]
            url=info.get("thumburl") or info.get("url")
            if not url or not re.search(r"\\.(jpg|jpeg|png)(\\?|$)",url,re.I):continue
            metadata=info.get("extmetadata",{})
            license_name=metadata.get("LicenseShortName",{}).get("value","")
            if not (license_name.startswith("CC") or license_name in ("Public domain","PD","CC0")):continue
            return {"url":url,"file":page["title"],"license":license_name,"credit":re.sub("<[^>]+>","",metadata.get("Artist",{}).get("value",""))[:180],"description_url":info.get("descriptionurl","")}
    except Exception as exc:print("Image lookup failed:",title,exc)
    return None
images={}
# Prefer original historical illustration from the cookbook if no licensed photograph.
historic=soup.find("img")
fallback=urllib.parse.urljoin(URL,historic.get("src","")) if historic else ""
for i,r in enumerate(records):
    photo=commons_image(r["title"])
    if photo:
        try:
            raw=get(photo["url"])
            if len(raw)>300 and len(raw)<3_000_000:
                ext=".png" if raw[:8]==b"\\x89PNG\\r\\n\\x1a\\n" else ".jpg"
                p=ROOT/"images"/(r["slug"]+ext);p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
                photo["local"]="images/"+p.name
        except Exception as exc:print("Download failed",r["title"],exc)
    r["image"]=photo or {"url":fallback,"license":"Historical book illustration (not dish-specific)","credit":"Fannie Merritt Farmer, 1910"}
    if i%30==0:print("Images:",i,"/",len(records),flush=True)
(ROOT/"recipes-archive.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
def esc(s):return html.escape(str(s),quote=True)
style="""@import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=IM+Fell+DW+Pica&display=swap');*{box-sizing:border-box}body{background:#e0d0ad;color:#362b20;margin:0;font:19px/1.5 'IM Fell DW Pica',Georgia,serif}header{background:#642b34;color:#f5e5c7;text-align:center;padding:22px}header a{color:inherit;text-decoration:none;font:30px 'IM Fell English',Georgia,serif}main{max-width:970px;margin:26px auto;padding:35px 55px;background:#f2e5c9;border:5px double #a88664;box-shadow:0 8px 30px #563e2225}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;text-align:center;color:#75413c}h1{font:italic 60px 'IM Fell English',Georgia,serif;text-align:center;color:#743e36;margin:10px 0}h2{font:italic 32px 'IM Fell English',serif;color:#743e36;border-bottom:1px solid #bca580}.sub{text-align:center;font-style:italic}.flourish{text-align:center;color:#9a7858;margin:15px}.columns{display:grid;grid-template-columns:1fr 1fr;gap:30px}.photo{border:1px solid #b39a75;padding:8px;margin:0}.photo img{width:100%;height:300px;object-fit:cover}.photo figcaption{font-size:12px;color:#695a48}.recipe-text p{margin:0 0 12px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:17px}.card{background:#f8edd7;border:1px solid #bca580;color:inherit;text-decoration:none}.card img{width:100%;height:155px;object-fit:cover}.card div{padding:12px}.card strong{font:italic 25px 'IM Fell English',serif;color:#743e36}.card small{display:block;color:#75604c}.search{width:100%;padding:12px;font:18px Georgia,serif;background:#fff8e8;border:1px solid #bca580}.source{border-top:3px double #bca580;padding-top:15px;margin-top:30px;font-size:15px}a{color:#743e36}footer{text-align:center;padding:20px;font-size:14px}@media(max-width:650px){main{padding:20px;margin:0;border-left:0;border-right:0}.columns{grid-template-columns:1fr}h1{font-size:42px}}"""
(ROOT/"style.css").write_text(style,encoding="utf-8")
cards=[]
for r in records:
    img=r["image"];src=img.get("local") or img.get("url") or fallback
    credit="Illustrative photograph; not an original period image" if img.get("local") else "Historical illustration; not necessarily of this dish"
    if img.get("description_url"):credit+=' · Wikimedia Commons: '+img.get("license","")
    body="".join("<p>"+esc(p)+"</p>" for p in r["parts"])
    page=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(r['title'])} · Antique Recipe Archive</title><link rel="stylesheet" href="../style.css"></head><body><header><a href="../index.html">The Antique Recipe Archive</a></header><main><a href="../index.html">← All recipes</a><p class="eyebrow">1910 · Fannie Merritt Farmer · {esc(r['chapter'])}</p><h1>{esc(r['title'])}</h1><p class="sub">The Boston Cooking-School Cook Book</p><div class="flourish">❧ ───── ❦ ───── ❧</div><div class="columns"><section><figure class="photo"><img src="{esc("../"+src if not src.startswith("http") else src)}" alt="Illustration associated with {esc(r['title'])}" onerror="this.style.display='none'"><figcaption>{esc(credit)} {('<a href="'+esc(img['description_url'])+'">Image attribution</a>') if img.get('description_url') else ''}</figcaption></figure><h2>Historical Recipe</h2><p>The following text is extracted from the 1910 edition, retaining historical terminology and quantities.</p></section><section class="recipe-text"><h2>Original Ingredients & Directions</h2>{body}</section></div><section class="source"><strong>Original source:</strong> Fannie Merritt Farmer, <em>The Boston Cooking-School Cook Book</em> (1910). <a href="{esc(URL)}">Read the digitized original</a>.<p>Automatically extracted transcription; editorial verification pending. Historical instructions may not meet modern food-safety standards.</p></section></main><footer>Preserving culinary history, one recipe at a time.</footer></body></html>"""
    folder=ROOT/"recipe";folder.mkdir(exist_ok=True)
    (folder/(r["slug"]+".html")).write_text(page,encoding="utf-8")
    cards.append(f'<a class="card" href="recipe/{esc(r["slug"])}.html"><img loading="lazy" src="{esc(src)}" alt="{esc(r["title"])}"><div><small>{esc(r["chapter"])} · 1910</small><strong>{esc(r["title"])}</strong></div></a>')
index=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Antique Recipe Archive · {len(records)} Original Recipes</title><link rel="stylesheet" href="style.css"></head><body><header><a href="index.html">The Antique Recipe Archive</a></header><main><p class="eyebrow">Fannie Merritt Farmer · 1910</p><h1>Recipes from Another Time</h1><p class="sub">{len(records)} original recipes drawn from a historic cookbook</p><div class="flourish">❧ ───── ❦ ───── ❧</div><p>Explore original recipes from the 1910 edition of <em>The Boston Cooking-School Cook Book</em>. Each recipe includes its source, original instructions, and an illustrative image. Automated transcriptions are awaiting editorial review.</p><input class="search" id="search" placeholder="Search historical recipes..." aria-label="Search recipes"><p id="count">{len(records)} recipes</p><div class="cards" id="cards">{''.join(cards)}</div></main><footer>Original source: <a href="{esc(URL)}">Project Gutenberg edition of Farmer's 1910 cookbook</a>. Illustrative images are not historical photographs.</footer><script>const s=document.getElementById('search'),cards=[...document.querySelectorAll('.card')],count=document.getElementById('count');s.addEventListener('input',()=>{{const q=s.value.toLowerCase();let n=0;for(const c of cards){{const ok=c.textContent.toLowerCase().includes(q);c.hidden=!ok;if(ok)n++}}count.textContent=n+' recipes'}})</script></body></html>"""
(ROOT/"index.html").write_text(index,encoding="utf-8")
print("Built",len(records),"authentic historical recipe pages",flush=True)
