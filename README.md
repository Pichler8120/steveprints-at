# StevePrints – 3D-Druck Onlineshop

Deine Website für 3D-gedruckte Designobjekte mit automatischer Etsy-Produktsynchronisation.

## 🚀 Setup

### 1. GitHub Repository erstellen

```bash
# Repository auf GitHub erstellen (steveprints-at)
# Dann zurück ins lokale Verzeichnis:

git remote add origin https://github.com/DEIN_USERNAME/steveprints-at.git
git branch -M main
git add -A
git commit -m "Initial commit: StevePrints Website mit Etsy-Sync"
git push -u origin main
```

### 2. Etsy API-Key sichern

1. Auf GitHub:
   - Settings → Secrets and variables → Actions → New repository secret
   - Name: `ETSY_API_KEY`
   - Value: `keystring:sharedsecret` (aus deiner `etsy_key.txt`)

2. Lokal ist die `etsy_key.txt` in `.gitignore` – wird nicht gepusht.

### 3. Cloudflare Pages aufsetzen

Das Deployment läuft über `.github/workflows/deploy-pages.yml` (Direct Upload via `wrangler`), nicht über die "Connect to Git" Integration.

1. GitHub Secrets anlegen (Repo → Settings → Secrets and variables → Actions):
   - `CLOUDFLARE_API_TOKEN` (Cloudflare Dashboard → API-Token des Kontos → Token mit "Edit Cloudflare Workers"-Vorlage)
   - `CLOUDFLARE_ACCOUNT_ID` (Cloudflare Dashboard → Account verwalten → Account ID)
2. Push auf `main` löst automatisch einen Deploy zum Pages-Projekt `steveprints-at` aus
3. **Domain verbinden:**
   - Deine Domäne `steveprints.at` ist bei helloly registriert
   - In Cloudflare: Domains → Domain verbinden → `steveprints.at` (DNS-Einträge automatisch importieren)
   - Nameserver bei helloly auf die von Cloudflare angezeigten Werte ändern (dauert bis zu 24-48h)
   - Danach im Pages-Projekt unter "Benutzerdefinierte Domains" → `steveprints.at` hinzufügen

### 4. Nightly Sync

Der GitHub Actions Workflow `.github/workflows/nightly-sync.yml`:
- Läuft täglich um **02:00 UTC** (3:00 CEST)
- Ruft Etsy-API auf → `index.html` aktualisiert
- Bilder werden in `images/` gespeichert
- Committed Änderungen automatisch zurück ins Repo
- **Cloudflare Pages wird automatisch neu deployed**

### 5. Bilder lokal testen

```bash
# Etsy-Sync manuell starten (lokal)
python3 etsy_sync.py

# Website öffnen
open index.html  # macOS
start index.html  # Windows
xdg-open index.html  # Linux
```

## 📁 Dateistruktur

```
steveprints-at/
├── index.html              # Deine Website (wird durch Sync aktualisiert)
├── etsy_sync.py            # Sync-Script
├── etsy_key.txt            # ⚠️  NICHT commiten (in .gitignore)
├── texte.json              # Produktnamen/Texte (bearbeitbar)
├── products.json           # Rohdaten von Etsy
├── images/                 # Heruntergeladene Produktbilder
│   └── *.jpg
├── .github/workflows/
│   ├── nightly-sync.yml    # Etsy-Sync Workflow
│   └── deploy-pages.yml    # Cloudflare Pages Deploy Workflow
├── .gitignore               # Secrets ausschließen
└── README.md                # Diese Datei
```

## ✍️ Produkttexte anpassen

Die `texte.json` enthält Namen und Kurzbeschreibungen für deine Produkte:

```json
{
  "12345678": {
    "name": "Mein schöner Druck",
    "text": "Eine tolle Beschreibung...",
    "info": "10 × 15 cm",
    "preis_ab": false
  }
}
```

- **name**: Wird als Überschrift auf der Karte angezeigt
- **text**: Kurzbeschreibung (automatisch aus Etsy-Beschreibung gefüllt, aber änderbar)
- **info**: Maße oder Verfügbarkeit (z.B. "3 verfügbar")
- **preis_ab**: `true`, wenn der Preis je nach Variante variiert

### Highlights (große gestapelte Karten)

Bis zu 4 Produkte bekommen eine große Karte in der „Kollektion“. Die übrigen erscheinen als Kacheln unter „Außerdem im Shop“. Highlight 1–3 bilden außerdem die Bild-Collage ganz oben.

```json
  "4569972046": {
    "name": "Deko Kürbisse 3er Set",
    "highlight": 1,
    "kategorie": "HERBST",
    "highlight_name": "Nordic Pumpkins",
    "highlight_text": "Drei Kürbisse im skandinavischen Stil …"
  }
```

- **highlight**: 1–4 = Position der großen Karte (weglassen = normale Kachel)
- **kategorie**: kleine Zeile oben auf der Karte („01 / HERBST“)
- **highlight_name** / **highlight_text**: optional eigener Titel/Text nur für die große Karte (sonst `name` / `text`)

Ist ein Highlight-Produkt auf Etsy nicht mehr aktiv, fällt die Karte beim nächsten Sync automatisch weg.

Nach der Bearbeitung der `texte.json` einfach `etsy_sync.py` nochmal laufen lassen.

### Sync-Optionen

```bash
python3 etsy_sync.py --dry-run    # Etsy abfragen, aber nichts speichern – zeigt die Änderungen an index.html
python3 etsy_sync.py --offline    # ohne Etsy: Seite aus products.json + texte.json neu bauen
```

## 🎨 Design

Design „Galerie“: Stile in `site.css` (gemeinsam für `index.html` und `datenschutz.html`), Schriften lokal in `fonts/`.

**Nach jeder Änderung an `site.css`** die Versionsnummer im Link hochzählen (`site.css?v=2` → `?v=3`, in `index.html` UND `datenschutz.html`). Cloudflare lässt Browser die CSS 4 Stunden zwischenspeichern – ohne neue Nummer sehen Besucher sonst noch das alte Design.
Scroll-Animationen sind reines CSS und nur aktiv, wenn der Browser `animation-timeline` kann und keine reduzierte Bewegung eingestellt ist – sonst wird alles statisch angezeigt.

### Druck-Effekt („Scroll – und es wird gedruckt“)

Bei jedem Seitenaufruf wählt ein kleines Inline-Skript zufällig ein Produkt (keine Cookies, keine externen Verbindungen). Ohne JavaScript bleibt Highlight 1 stehen. `index.html` ändert sich dadurch nur, wenn sich Produkte ändern. Steuerung in `texte.json`:

- **druck**: `false` nimmt ein Produkt aus der Rotation (z.B. Osterhase im Winter)
- **druck_schichten**: eigene Schichtzahl (sonst eine feste Zahl je Produkt zwischen 180 und 420)
- **druck_bild**: welches Etsy-Foto verwendet wird (1 = erstes)

## 🔍 Vorschau

Automatisch deployt wird nur `main` (= Live-Seite). Für eine Vorschau eines anderen Branches: GitHub → Actions → „Deploy to Cloudflare Pages“ → „Run workflow“ → Branch auswählen. Das Ergebnis liegt unter `https://<branch>.steveprints-at.pages.dev`; die Live-Seite bleibt unverändert.

## 🔄 Manueller Sync

Um die Website sofort zu aktualisieren (nicht bis zur nächsten Nacht warten):

1. Lokal ausführen:
   ```bash
   python3 etsy_sync.py
   git add -A
   git commit -m "Manual sync"
   git push
   ```

2. Oder in GitHub: Actions → Nightly Etsy Sync → Run workflow

## 🐛 Troubleshooting

**Fehler: "Kein API-Key gefunden"**
- Stelle sicher, dass `etsy_key.txt` lokal vorhanden ist
- Bei GitHub Actions: Secret `ETSY_API_KEY` ist konfiguriert?

**Bilder werden nicht angezeigt**
- Check: `images/` Ordner existiert und ist im Repo
- Browser-Cache löschen (Ctrl+Shift+Delete)

**Website wird nicht deployed**
- Cloudflare Pages Build-Log prüfen (Dashboard → Pages → Deployments)
- Sicherstellen, dass `main` Branch gepusht wurde

## 📞 Support

Alle Python-Fehler? Terminal öffnen und lokal testen:
```bash
python3 etsy_sync.py
```
Die Fehlermeldung hilft, das Problem zu finden.

---

**Fertig!** 🎉 Deine Website ist nun online und wird jede Nacht automatisch aktualisiert.
