"""
NMIXX stream tracker
Her çalıştırmada: veriyi çek -> data/history.json'a bugünün kaydını ekle -> docs/index.html üret.
"""
import json, os, re, datetime as dt, pathlib
import requests
from bs4 import BeautifulSoup

ARTIST_ID = os.environ.get("ARTIST_ID", "BURAYA_SPOTIFY_ARTIST_ID")  # open.spotify.com/artist/<BU KISIM>
ARTIST_NAME = "NMIXX"
UA = {"User-Agent": "Mozilla/5.0 (nmixx-tracker personal project)"}

ROOT = pathlib.Path(__file__).parent
HISTORY = ROOT / "data" / "history.json"
OUT = ROOT / "docs" / "index.html"


def num(s):
    return int(re.sub(r"[^\d]", "", s) or 0)


def fetch_tracks():
    """kworb.net'ten şarkı başına toplam + günlük stream."""
    url = f"https://kworb.net/spotify/artist/{ARTIST_ID}_songs.html"
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    for table in soup.find_all("table"):
        heads = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if "streams" in heads and "daily" in heads:
            tracks = {}
            for tr in table.find_all("tr"):
                td = tr.find_all("td")
                if len(td) < 3:
                    continue
                title = td[0].get_text(strip=True)
                tracks[title] = {"total": num(td[1].get_text()), "daily": num(td[2].get_text())}
            if tracks:
                return tracks
    raise RuntimeError("Şarkı tablosu bulunamadı (kworb sayfa yapısı değişmiş olabilir).")


def fetch_followers():
    """Resmi Spotify API (ücretsiz). Anahtar yoksa None döner."""
    cid, sec = os.environ.get("SPOTIFY_CLIENT_ID"), os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not (cid and sec):
        return None
    t = requests.post("https://accounts.spotify.com/api/token",
                      data={"grant_type": "client_credentials"}, auth=(cid, sec), timeout=30).json()
    a = requests.get(f"https://api.spotify.com/v1/artists/{ARTIST_ID}",
                     headers={"Authorization": f"Bearer {t['access_token']}"}, timeout=30).json()
    return a.get("followers", {}).get("total")


def fetch_listeners():
    """Aylık dinleyici: resmi API'de yok. kworb'dan en iyi çaba ile dener."""
    try:
        r = requests.get(f"https://kworb.net/spotify/artist/{ARTIST_ID}.html", headers=UA, timeout=30)
        m = re.search(r"Monthly\s+listeners[^\d]{0,40}([\d,]{5,})", r.text, re.I)
        return num(m.group(1)) if m else None
    except Exception:
        return None


def main():
    HISTORY.parent.mkdir(exist_ok=True)
    OUT.parent.mkdir(exist_ok=True)
    hist = json.loads(HISTORY.read_text("utf-8")) if HISTORY.exists() else {}

    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    hist[today] = {
        "listeners": fetch_listeners(),
        "followers": fetch_followers(),
        "tracks": fetch_tracks(),
    }
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False), "utf-8")

    html = TEMPLATE.replace("__DATA__", json.dumps(hist, ensure_ascii=False)).replace("__NAME__", ARTIST_NAME)
    OUT.write_text(html, "utf-8")
    print(f"OK {today}: {len(hist[today]['tracks'])} şarkı")


TEMPLATE = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME__ · günlük streamler</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,800&family=Figtree:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#15101f; --panel:#1e1730; --line:#2e2543; --text:#f3eefc; --mute:#9d92b8;
  --up:#6ee7b7; --down:#ff7a90; --bar:#3a2a63; --accent:#c9a7ff;
  color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:400 16px/1.5 Figtree,system-ui,sans-serif;
  padding:clamp(20px,5vw,64px);max-width:1040px;margin-inline:auto}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap}
h1{font:800 clamp(56px,13vw,128px)/.85 "Bricolage Grotesque",sans-serif;letter-spacing:-.04em;margin:0}
select{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:10px;
  padding:10px 14px;font:inherit}
select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.stats{display:flex;gap:clamp(24px,6vw,72px);flex-wrap:wrap;margin:48px 0 40px}
.stat b{display:block;font:600 clamp(28px,5vw,44px)/1.1 "Bricolage Grotesque",sans-serif;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums}
.stat span{color:var(--mute);font-size:14px}
.d{font-size:14px;font-variant-numeric:tabular-nums}
.up{color:var(--up)} .down{color:var(--down)} .flat{color:var(--mute)}
.head,.row{display:grid;grid-template-columns:2.2rem 1fr 7.5rem 7.5rem 5.5rem;gap:12px;align-items:center;padding:12px 14px}
.head{color:var(--mute);font-size:13px;border-bottom:1px solid var(--line)}
.row{border-radius:10px;position:relative;font-variant-numeric:tabular-nums;
  background:linear-gradient(90deg,var(--bar) var(--w),transparent var(--w))}
.row+.row{margin-top:2px}
.row .t{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.r{text-align:right}
.i{color:var(--mute)}
.row .daily{font-weight:600}
.empty{color:var(--mute);padding:32px 14px}
@media(max-width:640px){
  .head,.row{grid-template-columns:1.8rem 1fr 6rem 4.5rem}
  .total{display:none}
}
</style>
</head>
<body>
<header>
  <h1>__NAME__</h1>
  <select id="day" aria-label="Tarih"></select>
</header>

<section class="stats" id="stats"></section>

<div class="head"><span></span><span>Şarkı</span><span class="r total">Toplam</span><span class="r">Günlük</span><span class="r">Fark</span></div>
<main id="rows"></main>

<script>
const H = __DATA__;
const days = Object.keys(H).sort();
const fmt = n => n==null ? "–" : n.toLocaleString("tr-TR");
const delta = (n,cls="") => {
  if(n==null) return '<span class="flat d">–</span>';
  const c = n>0?"up":n<0?"down":"flat", s = n>0?"+":"";
  return `<span class="${c} d">${s}${fmt(n)}</span>`;
};
const sel = document.getElementById("day");
days.slice().reverse().forEach(d => sel.add(new Option(d, d)));
sel.onchange = () => render(sel.value);

function render(day){
  const cur = H[day], prev = H[days[days.indexOf(day)-1]];
  const sum = o => Object.values(o.tracks).reduce((a,t)=>a+t.total,0);
  const dd = (a,b) => (a==null||b==null) ? null : a-b;

  document.getElementById("stats").innerHTML = [
    ["Aylık dinleyici", cur.listeners, prev && dd(cur.listeners, prev.listeners)],
    ["Takipçi", cur.followers, prev && dd(cur.followers, prev.followers)],
    ["Toplam stream", sum(cur), prev && dd(sum(cur), sum(prev))],
  ].map(([l,v,d]) => `<div class="stat"><span>${l}</span><b>${fmt(v)}</b>${delta(d)}</div>`).join("");

  const list = Object.entries(cur.tracks).sort((a,b)=>b[1].daily-a[1].daily);
  const max = list.length ? list[0][1].daily || 1 : 1;
  document.getElementById("rows").innerHTML = list.length ? list.map(([name,t],i)=>{
    const p = prev && prev.tracks[name];
    const diff = p ? t.daily - p.daily : null;
    return `<div class="row" style="--w:${(t.daily/max*100).toFixed(1)}%">
      <span class="i">${i+1}</span><span class="t">${name}</span>
      <span class="r total">${fmt(t.total)}</span><span class="r daily">${fmt(t.daily)}</span>
      <span class="r">${delta(diff)}</span></div>`;
  }).join("") : '<p class="empty">Bu tarih için veri yok.</p>';
}
render(days[days.length-1]);
sel.value = days[days.length-1];
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
