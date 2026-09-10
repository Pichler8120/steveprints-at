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

1. Bei [Cloudflare Dashboard](https://dash.cloudflare.com) anmelden
2. **Pages** → Connect to Git
   - GitHub-Repo wählen: `steveprints-at`
   - Production branch: `main`
   - Build command: `echo 'Static site'`
   - Build output directory: `.`

3. **Domain verbinden:**
   - Deine Domäne `steveprints.at` ist bei helloly registriert
   - In Cloudflare: Zone hinzufügen → `steveprints.at`
   - Nameserver bei helloly ändern auf Cloudflare-Server (werden angezeigt)
   - Dann Custom Domain in Pages hinzufügen

### 4. Nightly Sync

Der GitHub Actions Workflow `.github/workflows/nightly-sync.yml`:
- Läuft täglich um **02:00 UTC** (3:00 CEST)
- Ruft Etsy-API auf → `steveprints.html` aktualisiert
- Bilder werden in `images/` gespeichert
- Committed Änderungen automatisch zurück ins Repo
- **Cloudflare Pages wird automatisch neu deployed**

### 5. Bilder lokal testen

```bash
# Etsy-Sync manuell starten (lokal)
python3 etsy_sync.py

# Website öffnen
open steveprints.html  # macOS
start steveprints.html  # Windows
xdg-open steveprints.html  # Linux
```

## 📁 Dateistruktur

```
steveprints-at/
├── steveprints.html          # Deine Website (wird durch Sync aktualisiert)
├── etsy_sync.py              # Sync-Script
├── etsy_key.txt              # ⚠️  NICHT commiten (in .gitignore)
├── texte.json                # Produktnamen/Texte (bearbeitbar)
├── products.json             # Rohdaten von Etsy
├── images/                   # Heruntergeladene Produktbilder
│   └── *.jpg
├── .github/workflows/
│   └── nightly-sync.yml      # GitHub Actions Workflow
├── .gitignore                # Secrets ausschließen
├── wrangler.toml             # Cloudflare Pages Config
└── README.md                 # Diese Datei
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

Nach der Bearbeitung der `texte.json` einfach `etsy_sync.py` nochmal laufen lassen.

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
