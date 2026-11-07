#!/usr/bin/env python3
"""Build a cached, episode-specific guest cast index from TVmaze."""
import json, re, time, urllib.request, urllib.parse, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
def get(url):
    for attempt in range(6):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Engage-TNG-guide/1.0 (GitHub Pages)"})
            with urllib.request.urlopen(req,timeout=25) as res:
                return json.load(res)
        except Exception:
            if attempt==5: raise
            time.sleep(min(30,2**attempt))
def norm(s):
    return re.sub(r'[^a-z0-9]','',s.lower())
def main():
    html=(ROOT/'index.html').read_text()
    start=html.index('const episodes=')+len('const episodes=')
    end=html.index('];',start)+1
    guide=json.loads(html[start:end])
    show=get('https://api.tvmaze.com/singlesearch/shows?q='+urllib.parse.quote('Star Trek: The Next Generation'))
    eps=get(f"https://api.tvmaze.com/shows/{show['id']}/episodes")
    lookup={(e['season'],norm(e['name'])):e for e in eps if e.get('number') is not None}
    by_season={}
    for e in eps:
        if e.get('number') is not None:
            by_season.setdefault(e['season'],[]).append(e)
    result={}
    missing=[]
    failures=[]
    for item in guide:
        key=f"{item['s']}-{item['e']}"
        ep=lookup.get((item['s'],norm(item['title'])))
        if not ep:
            # Streaming guides sometimes split two-part episodes or use different punctuation.
            candidates=by_season.get(item['s'],[])
            expected=item['e']
            if expected<=len(candidates):
                candidate=candidates[expected-1]
                if norm(item['title']).startswith(norm(candidate['name'])) or norm(candidate['name']).startswith(norm(item['title'])):
                    ep=candidate
        if not ep:
            missing.append(key+' '+item['title'])
            result[key]=[]
            continue
        try:
            raw=get(f"https://api.tvmaze.com/episodes/{ep['id']}/guestcast")
        except Exception as exc:
            failures.append(key+' '+str(exc))
            raw=[]
        credits=[]
        for c in raw:
            person=(c.get('person') or {}).get('name')
            character=(c.get('character') or {}).get('name')
            if person and character:
                credits.append({'actor':person,'character':character,'kind':'Guest'})
        result[key]=credits
        time.sleep(0.6)
    if missing:
        print('WARNING: Unmatched titles:', ', '.join(missing))
    if failures:
        print('WARNING: Failed guest credits:', ', '.join(failures))
    (ROOT/'cast.json').write_text(json.dumps({'source':'TVmaze','kind':'episode-specific guest credits','episodes':result,'unmatched':missing,'failures':failures},ensure_ascii=False,separators=(',',':'))+'\n')
    print(f"Cached guest cast for {len(result)} episodes; unmatched={len(missing)}, failures={len(failures)}")
if __name__=='__main__':main()
