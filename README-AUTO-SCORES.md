# Kamra Ta Muse Worlds Tracker — PandaScore auto scores

This version keeps the website static on GitHub Pages, but automatically refreshes `data.json` from PandaScore.

## Files

- `index.html` — tracker website
- `data.json` — normalized score feed read by the website
- `scripts/update_scores.py` — calls PandaScore and rewrites `data.json`
- `.github/workflows/update-scores.yml` — runs every 5 minutes and commits changed `data.json`
- `.nojekyll` — GitHub Pages compatibility

## 1. Get a PandaScore token

Create a PandaScore account and copy your API token.

Do NOT paste the token into `index.html`, `data.json`, or the Python script.

## 2. Add the GitHub secret

Repository → Settings → Secrets and variables → Actions → Secrets → New repository secret

Name:

PANDASCORE_TOKEN

Value:

your PandaScore API token

## 3. Optional but recommended: set the Worlds series ID

The updater tries to auto-detect the 2026 Worlds series.

For maximum reliability, create a repository variable:

Repository → Settings → Secrets and variables → Actions → Variables → New repository variable

Name:

PANDASCORE_SERIES_ID

Value:

the PandaScore series ID for Worlds 2026

If you leave this blank, the script will try to find the series automatically.

## 4. Upload these files to main

The paths must be exactly:

index.html
data.json
.nojekyll
scripts/update_scores.py
.github/workflows/update-scores.yml

## 5. Run it once manually

GitHub → Actions → Update PandaScore data → Run workflow

Open the run and make sure all steps are green.

The workflow will then run approximately every 5 minutes.

## 6. What updates automatically

The website matches PandaScore fixtures to your manually selected teams by team name/acronym.

When it finds the same two teams in PandaScore, it overlays PandaScore's current series score in:

- Play-In
- Swiss scored matches (2-0, 0-2, 2-1, 2-2)
- Knockout

Bracket placement and Swiss progression remain manual.

The browser checks `data.json` once per minute. GitHub Actions refreshes `data.json` on a 5-minute schedule, so this is not second-by-second live scoring.

## Troubleshooting

### Action says PANDASCORE_TOKEN is missing
Add the repository secret exactly as `PANDASCORE_TOKEN`.

### Auto-detection cannot find Worlds 2026
Set `PANDASCORE_SERIES_ID` as a repository variable.

### git push returns 403
Repository → Settings → Actions → General → Workflow permissions → enable Read and write permissions.

The workflow itself also requests `contents: write`.

### A team is not matching
The site matches PandaScore's team name/acronym against your tracker's team name/short code. If PandaScore uses a different name, add an alias in `trackerShortForOpponent()` in `index.html`.
