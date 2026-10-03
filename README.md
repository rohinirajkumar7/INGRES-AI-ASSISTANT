# 💧 INGRES AI Chatbot

Ask India's groundwater data questions in plain language (8 languages). Built on the
CGWB / INGRES 2024-25 assessment (726 assessment units, 37 states & UTs).

**Stack:** React (frontend) · FastAPI on Vercel Python functions (backend) · Gemini free tier (language understanding) · plain CSV data. **No database, no Rasa, one Vercel project.**

## Features
- Look up any state or district: rainfall, extraction stage, recharge, net availability
- Compare places, rank them (“top 5 over-exploited districts in Punjab”), count categories
- Interactive India tile map coloured by the official CGWB categories (Safe / Semi-critical / Critical / Over-exploited) — tap a state to ask about it
- Follow-up questions (“and its recharge?”), voice input and read-aloud, typo-tolerant place names (“Banglore”)
- **Works without any API key** (rule-based mode); add a Gemini key for natural language in 8 languages

## Add your API key (do this later, whenever you like)
1. Get a free key: https://aistudio.google.com/apikey
2. **Local:** `cp .env.example .env` and set `GEMINI_API_KEY=...`
3. **Vercel:** Project → Settings → Environment Variables → add `GEMINI_API_KEY` → redeploy.
4. Check `/api/health`: `"gemini_configured": true`.

Model ids live in `GEMINI_MODEL` / `GEMINI_FALLBACK_MODEL` (defaults are the `*-latest` aliases, so deprecations don't break you). The free tier is rate limited; on a 429 the app cools down for 20s and answers with the offline rules instead of failing.

## Deploy to Vercel (only Vercel)
1. Push this folder to GitHub → *Add New Project* on Vercel → import it. Leave the framework as “Other”; `vercel.json` sets everything.
2. Add `GEMINI_API_KEY` (optional) and deploy. Frontend and `/api/*` are served from the same domain.

## Run locally
```bash
pip install -r requirements-dev.txt
uvicorn api.index:app --port 8000 --reload      # backend
cd frontend && npm install && npm start         # frontend on :3000 (proxies /api)
```

## Tests
```bash
python -m pytest -q          # backend (60 tests; HTTP tests need fastapi installed)
cd frontend && npm test      # frontend utils
```
Vercel doesn't run tests itself; `.github/workflows/ci.yml` runs both on every push.

## Project layout
```
api/index.py        Vercel entrypoint (exports the ASGI app)
ingres/             data.py · locations.py · nlu.py · gemini.py · service.py · app.py · geo.py
ingres/data/        groundwater.csv (generated)
scripts/            build_dataset.py  (xlsx -> csv, only needed if the data changes)
data/source/        original ingres-data.xlsx
frontend/           React app
tests/              unit + API tests
```

## What changed vs. the original project
| Problem | Fix |
|---|---|
| Loader read only the first (“C”) sub-column of each measure → wrong/zero values | Reads the **Total** columns |
| `/stats/total` shadowed by `/stats/{state}` (404) | Route order fixed + regression test |
| “rainfall in Delhi” answered with a greeting (`hi` substring) | Whole-word matching, data intents first |
| Every `/chat` loaded the whole table | Data loaded once, indexed once |
| DB wiped & reloaded each start; Rasa not deployable on Vercel | CSV in memory; Rasa & Postgres removed |
| CORS `*` with credentials | No credentials; `CORS_ORIGINS` env var |
| State stage = mean of district %, 637-line keyword map | Weighted stage; Gemini NLU + small rule fallback |

Notes: state rainfall is area-weighted; districts with no reported resource show “No data”.
