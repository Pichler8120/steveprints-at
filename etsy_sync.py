#!/usr/bin/env python3
"""
StevePrints – Etsy-Sync

Holt die aktiven Listings des Shops ueber die Etsy Open API v3 und schreibt
den Produktbereich der Website neu. Braucht nur den API-Key, kein OAuth.

Aufruf:
    ETSY_API_KEY=dein_key python3 etsy_sync.py

Oder Key in eine Datei "etsy_key.txt" neben dieses Skript legen.
"""

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
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    # Hash des URLs als Dateiname, um Duplikate zu vermeiden
    filename = hashlib.sha256(url.encode()).hexdigest()[:16] + ".jpg"
    filepath = os.path.join(IMAGES_DIR, filename)

    # Wenn schon heruntergeladen, nicht nochmal anfragen
    if os.path.exists(filepath):
        return f"{IMAGES_DIR}/{filename}"

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
    with open(TEXT_FILE, "w", encoding="utf-8") as fh:
        json.dump(texts, fh, ensure_ascii=False, indent=2)
    return texts, added


def card(listing, entry):
    url = listing.get("url") or f"https://www.etsy.com/listing/{listing['listing_id']}"
    images = listing.get("images", [])
    if not images:
        return ""

    name = html.escape(entry.get("name") or short_name(listing))
    text = html.escape(entry.get("text") or "")
    info = html.escape(entry.get("info") or "")

    alt_img = ""
    if len(images) > 1:
        alt_img = f'\n          <img class="alt" src="{images[1]}" alt="{name} \u2013 zweite Ansicht">'

    return f"""      <a class="card rv" href="{url}" target="_blank" rel="noopener">
        <div class="shot">
          <img src="{images[0]}" alt="{name}">{alt_img}
        </div>
        <h3>{name}</h3>
        <p class="sub">{text}</p>
        <div class="meta"><span>{info}</span><span class="price">{price(listing, entry)}</span></div>
        <span class="go">Auf Etsy ansehen \u2192</span>
      </a>"""


def hero_block(listings, texts):
    """Grosses Bild oben: bei jedem Seitenaufruf ein zufaelliges Produkt."""
    pool = []
    for l in listings:
        images = l.get("images") or []
        if not images:
            continue
        entry = texts.get(str(l["listing_id"]), {})
        pool.append({
            "img": images[0],
            "name": entry.get("name") or short_name(l),
            "url": l.get("url") or f"https://www.etsy.com/listing/{l['listing_id']}",
        })
    if not pool:
        return ""

    first = pool[0]
    data = json.dumps(pool, ensure_ascii=False)
    return f"""{HERO_START}
    <figure class="heroshot" style="margin:0">
      <a href="{first['url']}" target="_blank" rel="noopener" id="heroLink">
        <img id="heroImg" src="{first['img']}" alt="{html.escape(first['name'])}">
      </a>
      <figcaption id="heroCap">{html.escape(first['name'])}</figcaption>
    </figure>
    <script>
      (function(){{
        var pool = {data};
        var pick = pool[Math.floor(Math.random() * pool.length)];
        document.getElementById('heroImg').src = pick.img;
        document.getElementById('heroImg').alt = pick.name;
        document.getElementById('heroCap').textContent = pick.name;
        document.getElementById('heroLink').href = pick.url;
      }})();
    </script>
    {HERO_END}"""


# ----------------------------------------------------------------- Schreiben

def replace_block(page, start, end, block):
    return re.sub(re.escape(start) + ".*?" + re.escape(end), lambda _: block, page, flags=re.S)


def update_site(cards, hero=""):
    if not os.path.exists(SITE_FILE):
        sys.exit(f"{SITE_FILE} nicht gefunden. Skript in denselben Ordner legen.")
    with open(SITE_FILE, encoding="utf-8") as fh:
        page = fh.read()
    if START not in page or END not in page:
        sys.exit(f"Marker {START} / {END} fehlen in {SITE_FILE}.")

    block = START + "\n" + "\n\n".join(cards) + "\n      " + END
    page = replace_block(page, START, END, block)
    if hero and HERO_START in page and HERO_END in page:
        page = replace_block(page, HERO_START, HERO_END, hero)
    with open(SITE_FILE, "w", encoding="utf-8") as fh:
        fh.write(page)


def main():
    key = api_key()
    listings = fetch_listings(key)
    listings.sort(key=lambda l: l.get("original_creation_timestamp", 0), reverse=True)

    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(listings, fh, ensure_ascii=False, indent=2)

    texts, added = merge_texts(listings)
    cards = [c for c in (card(l, texts.get(str(l["listing_id"]), {})) for l in listings) if c]
    if not cards:
        sys.exit("Keine Listings mit Bildern gefunden, Website bleibt unveraendert.")

    update_site(cards, hero_block(listings, texts))
    print(f"{len(cards)} Produkte uebernommen:")
    for l in listings:
        e = texts.get(str(l["listing_id"]), {})
        print(f"  \u00b7 {e.get('name', '')}  {price(l, e)}")
    if added:
        print(f"\nNeu in {TEXT_FILE} eingetragen: " + ", ".join(added))
        print(f"Namen und Texte kannst du dort anpassen, dann Skript nochmal starten.")


if __name__ == "__main__":
    main()
