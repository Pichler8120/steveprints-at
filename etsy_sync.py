#!/usr/bin/env python3
"""
StevePrints – Etsy-Sync

Holt die aktiven Listings des Shops ueber die Etsy Open API v3 und schreibt
den Produktbereich der Website neu. Braucht nur den API-Key, kein OAuth.

Aufruf:
    ETSY_API_KEY=dein_key python3 etsy_sync.py

Oder Key in eine Datei "etsy_key.txt" neben dieses Skript legen.

Optionen:
    --dry-run   nichts schreiben (keine Bilder, kein JSON, keine index.html);
                zeigt nur, was sich aendern wuerde
    --offline   Etsy nicht abfragen, sondern products.json vom letzten Lauf nehmen
                (praktisch, um nach Aenderungen an texte.json oder am Design
                die Seite neu zu bauen)

Seitenaufbau (Design "Galerie"):
    HERO        Bild-Collage oben  = Highlights 1, 3, 2
    HIGHLIGHTS  4 grosse gestapelte Karten = Produkte mit "highlight": 1-4 in texte.json
    PRODUCTS    Kacheln "Ausserdem im Shop" = alle uebrigen aktiven Produkte
    PRINT       Druck-Effekt: jeden Tag ein anderes Produkt (Rotation nach Datum)
"""

import argparse
import datetime
import difflib
import html
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# ----------------------------------------------------------------- Einstellungen

SHOP_ID = 64420903                 # StevePrintsAT
SITE_FILE = "index.html"           # wird direkt bearbeitet
DATA_FILE = "products.json"        # Rohdaten, praktisch zum Nachschauen
TEXT_FILE = "texte.json"           # deine eigenen Namen und Kurztexte
IMAGES_DIR = "images"              # Ordner fuer heruntergeladene Bilder
LOCALE = "de"                      # Sprache der Etsy-Uebersetzungen
API = "https://openapi.etsy.com/v3/application"

START = "<!-- PRODUCTS:START -->"
END = "<!-- PRODUCTS:END -->"
HERO_START = "<!-- HERO:START -->"
HERO_END = "<!-- HERO:END -->"
HL_START = "<!-- HIGHLIGHTS:START -->"
HL_END = "<!-- HIGHLIGHTS:END -->"
PRINT_START = "<!-- PRINT:START -->"
PRINT_END = "<!-- PRINT:END -->"

# Druck-Effekt: Schichthoehe im Text, Bereich fuer die automatisch erzeugte Schichtzahl
LAYER_HEIGHT = "0,2"
LAYER_RANGE = (180, 420)

# Anzahl der grossen Highlight-Karten (Farbthemen t1-t4 in site.css)
MAX_HIGHLIGHTS = 4

DRY_RUN = False

# Wie viele Woerter der Etsy-Beschreibung als Kurztext auf die Karte kommen.
BLURB_WORDS = 26


# ----------------------------------------------------------------- API-Zugriff

def api_key():
    """Etsy verlangt seit 09.02.2026 'keystring:secret' im x-api-key-Header.

    Akzeptiert wird entweder eine Zeile "keystring:secret" oder zwei Zeilen
    (Keystring, dann Shared Secret).
    """
    raw = os.environ.get("ETSY_API_KEY")
    if not raw:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(here, "etsy_key.txt")
        if not os.path.exists(path):
            sys.exit(
                "Kein API-Key gefunden.\n"
                "Entweder ETSY_API_KEY setzen oder etsy_key.txt neben das Skript legen."
            )
        with open(path, encoding="utf-8-sig") as fh:
            raw = fh.read()

    parts = [p.strip() for p in raw.replace(":", "\n").splitlines() if p.strip()]
    if len(parts) < 2:
        sys.exit(
            "Es fehlt das Shared Secret.\n"
            "Etsy braucht seit Februar 2026 beides. In etsy_key.txt gehoert:\n"
            "    keystring:sharedsecret\n"
            "Beide Werte stehen auf https://www.etsy.com/developers/your-apps"
        )
    return f"{parts[0]}:{parts[1]}"


def get(path, key, **params):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        sys.exit(f"Etsy antwortet mit {exc.code} auf {path}\n{body}")
    except urllib.error.URLError as exc:
        sys.exit(f"Keine Verbindung zu Etsy: {exc.reason}")


def download_image(url):
    """Laed ein Bild herunter und speichert es lokal.

    Gibt den lokalen Pfad zurueck (relativ, fuer die HTML).
    """
    # Hash des URLs als Dateiname, um Duplikate zu vermeiden
    filename = hashlib.sha256(url.encode()).hexdigest()[:16] + ".jpg"
    filepath = os.path.join(IMAGES_DIR, filename)

    # Wenn schon heruntergeladen, nicht nochmal anfragen
    if os.path.exists(filepath):
        return f"{IMAGES_DIR}/{filename}"

    if DRY_RUN:
        print(f"  [dry-run] neues Bild wuerde geladen: {filepath}")
        return f"{IMAGES_DIR}/{filename}"

    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(filepath, "wb") as fh:
                fh.write(resp.read())
        return f"{IMAGES_DIR}/{filename}"
    except Exception as e:
        print(f"Warnung: Konnte {url} nicht herunterladen: {e}", file=sys.stderr)
        return url  # Fallback auf original URL


def fetch_listings(key):
    """Aktive Listings inklusive Bildern."""
    data = get(f"/shops/{SHOP_ID}/listings/active", key, limit=100)
    listings = data.get("results", [])
    if not listings:
        sys.exit("Etsy liefert keine aktiven Listings zurueck.")

    ids = [str(l["listing_id"]) for l in listings]
    detail = get(
        "/listings/batch", key,
        listing_ids=",".join(ids), includes="Images", language=LOCALE,
    )
    by_id = {d["listing_id"]: d for d in detail.get("results", [])}

    for l in listings:
        full = by_id.get(l["listing_id"], {})
        remote_urls = [
            img.get("url_794xN") or img.get("url_fullxfull")
            for img in full.get("images", [])
            if img.get("url_794xN") or img.get("url_fullxfull")
        ]
        # Bilder lokal speichern
        l["images"] = [download_image(url) for url in remote_urls]
        # Uebersetzte Fassung bevorzugen, falls vorhanden
        for field in ("title", "description"):
            if full.get(field):
                l[field] = full[field]
    return listings


# ----------------------------------------------------------------- Aufbereiten

def price(listing, entry=None):
    p = listing.get("price") or {}
    amount, divisor = p.get("amount"), p.get("divisor") or 100
    if amount is None:
        return ""
    value = amount / divisor
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    symbol = {"EUR": "\u20ac", "USD": "$"}.get(p.get("currency_code"), "")
    prefix = "ab " if (entry or {}).get("preis_ab") else ""
    return f"{prefix}{text}\u00a0{symbol}".strip()


def blurb(listing):
    text = (listing.get("description") or "").replace("\r", "\n")
    # Erste sinnvolle Zeile nehmen, Aufzaehlungen und Ueberschriften ueberspringen
    for line in text.split("\n"):
        line = line.strip(" \t*\u2022-")
        if len(line) > 45 and not line.isupper():
            words = line.split()
            if len(words) > BLURB_WORDS:
                line = " ".join(words[:BLURB_WORDS]).rstrip(".,;:") + " \u2026"
            return html.escape(line)
    return ""


def dimensions(listing):
    w, h = listing.get("item_width"), listing.get("item_height")
    unit = {"cm": "cm", "mm": "mm", "in": "in"}.get(listing.get("item_dimensions_unit"), "")
    parts = [f"{float(v):g}".replace(".", ",") for v in (w, h) if v]
    if parts and unit:
        return " \u00d7 ".join(parts) + " " + unit
    qty = listing.get("quantity")
    return f"{qty} verf\u00fcgbar" if qty else ""


def short_name(listing):
    """Etsy-Titel sind fuer die Suche geschrieben. Erste Sinneinheit reicht."""
    title = listing.get("title", "").strip()
    for sep in ("\u2013", "\u2014", " - ", ","):
        if sep in title:
            title = title.split(sep)[0]
            break
    return " ".join(title.split())[:60].strip(" -\u2013")


def load_texts():
    if not os.path.exists(TEXT_FILE):
        return {}
    with open(TEXT_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def merge_texts(listings):
    """Bestehende Eintraege bleiben, neue Produkte werden vorbefuellt."""
    texts = load_texts()
    texts.setdefault("_hinweis", (
        "Hier bestimmst du, wie die Produkte auf der Website heissen. "
        "name = Ueberschrift, text = Satz darunter, info = Zeile links unten, "
        "preis_ab = true, wenn der Preis je nach Variante steigt. "
        "Neue Etsy-Produkte werden beim naechsten Lauf automatisch ergaenzt."
    ))
    texts.setdefault("_hinweis_highlights", (
        "Grosse Karten oben in der Kollektion: highlight = 1 bis 4 (Reihenfolge), "
        "kategorie = kleine Zeile oben (z.B. HERBST), highlight_name / highlight_text = "
        "optional eigener Titel und Text nur fuer die grosse Karte (sonst name / text). "
        "Die Highlights 1-3 bilden ausserdem die Bild-Collage ganz oben. Alle anderen "
        "Produkte erscheinen als Kacheln unter 'Ausserdem im Shop'."
    ))
    texts.setdefault("_hinweis_druck", (
        "Druck-Effekt ('Scroll - und es wird gedruckt'): jeden Tag ein anderes Produkt. "
        "druck = false nimmt ein Produkt aus der Rotation, druck_schichten = eigene "
        "Schichtzahl (sonst eine feste Zahl je Produkt), druck_bild = welches Etsy-Foto "
        "(1 = erstes)."
    ))
    added = []
    for l in listings:
        key = str(l["listing_id"])
        if key not in texts:
            texts[key] = {
                "name": short_name(l),
                "text": blurb(l),
                "info": dimensions(l),
                "preis_ab": False,
            }
            added.append(texts[key]["name"])
    if not DRY_RUN:
        with open(TEXT_FILE, "w", encoding="utf-8") as fh:
            json.dump(texts, fh, ensure_ascii=False, indent=2)
    return texts, added


def esc(value):
    """Texte aus texte.json duerfen schon Entities enthalten (z.B. &amp;) - nicht doppelt escapen."""
    return html.escape(html.unescape(value or ""))


def listing_url(listing):
    return listing.get("url") or f"https://www.etsy.com/listing/{listing['listing_id']}"


def tile(listing, entry):
    """Kachel 'Ausserdem im Shop'."""
    images = listing.get("images", [])
    if not images:
        return ""
    name = esc(entry.get("name") or short_name(listing))
    alt_img = ""
    if len(images) > 1:
        alt_img = (f'\n          <img class="alt" src="{images[1]}" alt="" '
                   f'loading="lazy" decoding="async">')
    return f"""      <a class="tile reveal" href="{listing_url(listing)}" target="_blank" rel="noopener">
        <div class="shot">
          <img src="{images[0]}" alt="{name}" loading="lazy" decoding="async">{alt_img}
        </div>
        <div class="row"><span>{name}</span><span class="price">{price(listing, entry)}</span></div>
      </a>"""


def feature(listing, entry, index):
    """Grosse gestapelte Highlight-Karte (index 0-3)."""
    images = listing.get("images", [])
    if not images:
        return ""
    name = esc(entry.get("highlight_name") or entry.get("name") or short_name(listing))
    text = esc(entry.get("highlight_text") or entry.get("text") or "")
    cat = esc(entry.get("kategorie") or "")
    tag = f"{index + 1:02d}" + (f" / {cat}" if cat else "")
    return f"""      <a class="feature t{index % 4 + 1}" style="--i:{index}" href="{listing_url(listing)}" target="_blank" rel="noopener">
        <div class="pic"><img src="{images[0]}" alt="{name}" loading="lazy" decoding="async"></div>
        <div class="body">
          <span class="tag">{tag}</span>
          <div class="txt">
            <h3>{name}</h3>
            <p>{text}</p>
          </div>
          <div class="foot"><span class="price">{price(listing, entry)}</span><span class="go">Auf Etsy ansehen \u2197</span></div>
        </div>
      </a>"""


def split_highlights(listings, texts):
    """Teilt in (Highlights nach Nummer sortiert, Rest in Etsy-Reihenfolge)."""
    ranked = []
    for l in listings:
        entry = texts.get(str(l["listing_id"]), {})
        try:
            rank = int(entry.get("highlight") or 0)
        except (TypeError, ValueError):
            rank = 0
        if rank > 0 and l.get("images"):
            ranked.append((rank, l))
    ranked.sort(key=lambda t: t[0])
    highlights = [l for _, l in ranked[:MAX_HIGHLIGHTS]]
    chosen = {l["listing_id"] for l in highlights}
    rest = [l for l in listings if l["listing_id"] not in chosen]
    return highlights, rest


def hero_block(highlights, rest, texts):
    """Collage oben: grosses Bild = Highlight 1, rechts Highlight 3 und 2 (wie im Entwurf)."""
    pool = [highlights[i] for i in (0, 2, 1) if i < len(highlights)]
    for l in rest:  # auffuellen, falls weniger als 3 Highlights gesetzt sind
        if len(pool) >= 3:
            break
        if l.get("images"):
            pool.append(l)
    if not pool:
        return ""
    items = []
    for i, l in enumerate(pool):
        entry = texts.get(str(l["listing_id"]), {})
        name = esc(entry.get("name") or short_name(l))
        load = 'fetchpriority="high"' if i == 0 else 'decoding="async"'
        items.append(
            f'      <a href="{listing_url(l)}" target="_blank" rel="noopener">'
            f'<img src="{l["images"][0]}" alt="{name}" {load}></a>'
        )
    return HERO_START + "\n" + "\n".join(items) + "\n      " + HERO_END


def layer_count(listing, entry):
    """Eigene Zahl aus texte.json, sonst eine feste, plausible Zahl je Produkt (aus der Listing-ID)."""
    try:
        own = int(entry.get("druck_schichten") or 0)
    except (TypeError, ValueError):
        own = 0
    if own > 0:
        return own
    lo, hi = LAYER_RANGE
    digest = hashlib.sha256(str(listing["listing_id"]).encode()).digest()
    return lo + int.from_bytes(digest[:4], "big") % (hi - lo + 1)


def print_block(listings, texts, day=None):
    """Druck-Effekt: Produkt des Tages, reihum durch alle Produkte mit Bild (ohne druck = false)."""
    pool = []
    for l in sorted(listings, key=lambda x: x["listing_id"]):  # stabile Reihenfolge
        entry = texts.get(str(l["listing_id"]), {})
        if entry.get("druck") is False or not l.get("images"):
            continue
        pool.append((l, entry))
    if not pool:
        return ""
    day = day or datetime.date.today()
    l, entry = pool[day.toordinal() % len(pool)]

    try:
        img_index = max(int(entry.get("druck_bild") or 1) - 1, 0)
    except (TypeError, ValueError):
        img_index = 0
    images = l["images"]
    img = images[img_index] if img_index < len(images) else images[0]
    name = esc(entry.get("highlight_name") or entry.get("name") or short_name(l))
    alt = esc(entry.get("name") or short_name(l))
    n = layer_count(l, entry)
    return f"""{PRINT_START}
  <div class="print-stage" style="--layers:{n}">
    <div class="print-copy">
      <p class="eyebrow">Live aus der Werkstatt</p>
      <h2 id="print-title" class="display">Scroll \u2013 und es wird gedruckt.</h2>
      <div class="layer-count">
        <span class="lbl">SCHICHT</span>
        <span class="num"><span class="static">{n}</span></span>
        <span class="tot">/ {n}</span>
      </div>
      <p class="print-done"><strong>Fertig.</strong> {name}, {LAYER_HEIGHT}&nbsp;mm pro Schicht, gedruckt in Peggau \u2013 und genau so entsteht jedes St\u00fcck, das du bei mir bestellst.</p>
    </div>
    <div class="print-bed">
      <div class="grid" aria-hidden="true"></div>
      <img src="{img}" alt="{alt}, Schicht f\u00fcr Schicht gedruckt" loading="lazy" decoding="async">
      <div class="lines" aria-hidden="true"></div>
      <div class="nozzle" aria-hidden="true"><div class="beam"></div><div class="tip"></div></div>
    </div>
  </div>
  {PRINT_END}"""


# ----------------------------------------------------------------- Schreiben

def replace_block(page, start, end, block):
    return re.sub(re.escape(start) + ".*?" + re.escape(end), lambda _: block, page, flags=re.S)


def update_site(tiles, features, hero, printed=""):
    if not os.path.exists(SITE_FILE):
        sys.exit(f"{SITE_FILE} nicht gefunden. Skript in denselben Ordner legen.")
    with open(SITE_FILE, encoding="utf-8") as fh:
        old = fh.read()
    for a, b in ((START, END), (HL_START, HL_END), (HERO_START, HERO_END), (PRINT_START, PRINT_END)):
        if a not in old or b not in old:
            sys.exit(f"Marker {a} / {b} fehlen in {SITE_FILE}.")

    page = replace_block(old, START, END, START + "\n" + "\n\n".join(tiles) + "\n      " + END)
    page = replace_block(page, HL_START, HL_END,
                         HL_START + "\n" + "\n\n".join(features) + "\n      " + HL_END)
    if hero:
        page = replace_block(page, HERO_START, HERO_END, hero)
    if printed:
        page = replace_block(page, PRINT_START, PRINT_END, printed)

    if DRY_RUN:
        diff = list(difflib.unified_diff(
            old.splitlines(), page.splitlines(), SITE_FILE, SITE_FILE + " (neu)", lineterm="", n=1))
        if diff:
            print(f"\n[dry-run] {SITE_FILE} wuerde sich so aendern:")
            print("\n".join(diff))
        else:
            print(f"\n[dry-run] {SITE_FILE} bliebe unveraendert.")
        return
    with open(SITE_FILE, "w", encoding="utf-8") as fh:
        fh.write(page)


def main():
    global DRY_RUN
    ap = argparse.ArgumentParser(description="Etsy-Produkte in index.html uebernehmen")
    ap.add_argument("--dry-run", action="store_true", help="nichts schreiben, nur Aenderungen zeigen")
    ap.add_argument("--offline", action="store_true", help="products.json statt Etsy-API verwenden")
    args = ap.parse_args()
    DRY_RUN = args.dry_run

    if args.offline:
        if not os.path.exists(DATA_FILE):
            sys.exit(f"{DATA_FILE} fehlt - fuer --offline braucht es einen frueheren Lauf.")
        with open(DATA_FILE, encoding="utf-8") as fh:
            listings = json.load(fh)
    else:
        listings = fetch_listings(api_key())
    listings.sort(key=lambda l: l.get("original_creation_timestamp", 0), reverse=True)

    if not args.offline and not DRY_RUN:
        with open(DATA_FILE, "w", encoding="utf-8") as fh:
            json.dump(listings, fh, ensure_ascii=False, indent=2)

    texts, added = merge_texts(listings)

    def entry(l):
        return texts.get(str(l["listing_id"]), {})

    highlights, rest = split_highlights(listings, texts)
    features = [c for c in (feature(l, entry(l), i) for i, l in enumerate(highlights)) if c]
    tiles = [c for c in (tile(l, entry(l)) for l in rest) if c]
    if not features and not tiles:
        sys.exit("Keine Listings mit Bildern gefunden, Website bleibt unveraendert.")

    printed = print_block(listings, texts)
    update_site(tiles, features, hero_block(highlights, rest, texts), printed)
    print(f"\n{len(features) + len(tiles)} Produkte uebernommen"
          + (" (Trockenlauf, nichts gespeichert)" if DRY_RUN else "") + ":")
    for l in highlights:
        print(f"  * {entry(l).get('name', '')}  {price(l, entry(l))}  (Highlight {entry(l).get('highlight')})")
    for l in rest:
        print(f"  \u00b7 {entry(l).get('name', '')}  {price(l, entry(l))}")
    if printed:
        today = re.search(r"--layers:(\d+)", printed).group(1)
        who = re.search(r'alt="(.*?), Schicht', printed).group(1)
        print(f"\nDruck-Effekt heute: {html.unescape(who)} ({today} Schichten)")
    if len(highlights) < MAX_HIGHLIGHTS:
        print(f"\nHinweis: nur {len(highlights)} von {MAX_HIGHLIGHTS} Highlights aktiv "
              f"(\"highlight\": 1-{MAX_HIGHLIGHTS} in {TEXT_FILE} setzen).")
    if added:
        print(f"\nNeu in {TEXT_FILE} eingetragen: " + ", ".join(added))
        print("Namen und Texte kannst du dort anpassen, dann Skript nochmal starten.")


if __name__ == "__main__":
    main()
