#  INGRES AI Chatbot

**Ask India's groundwater data questions in plain language, in 8 languages.**

A chatbot built on the CGWB / INGRES **2024-25 groundwater assessment** (726 assessment units across 37 states and UTs). Type a question like *"Rainfall in Bengaluru"* or tap a state on the interactive India map, and get an answer with data cards, charts and follow-up suggestions.

It works with **no API key for English questions** (rule-based mode). Add a free Gemini key to understand free-form phrasing and place names written in Hindi, Kannada, Telugu, Tamil, Marathi, Bengali and Gujarati.

## Features

- **Look up any state or district:** rainfall, stage of extraction, annual recharge and net availability for future use.
- **Compare and rank:** *"Compare Karnataka and Kerala"*, *"Top 5 over-exploited districts in Punjab"*, *"How many districts are over-exploited?"*
- **Interactive India map:** every state is coloured by its official CGWB category. Tap a state to ask about it.
- **Follow-up questions:** *"and its recharge?"* remembers the place you were just talking about.
- **Typo-tolerant place names:** *"Banglore"* still finds Bengaluru.
- **Voice input and read-aloud** in the browser.
- **8 languages**, with auto-detection from the script you type in. Non-English place names need a Gemini key (see below).
- **Graceful fallback:** if Gemini is missing or rate limited, the app answers English questions with offline rules instead of failing.

### What the map colours mean

Each state is coloured by its **stage of groundwater extraction** (extraction ÷ extractable resource), using the official CGWB thresholds:

| Colour | Category | Stage of extraction |
|---|---|---|
| 🟩 Green | Safe | up to 70% |
| 🟨 Yellow | Semi-critical | 70% – 90% |
| 🟧 Orange | Critical | 90% – 100% |
| 🟥 Red | Over-exploited | above 100% (more is taken out than is recharged) |
| ⬜ Grey | No data | not reported |

The state value is a **weighted** stage computed from its districts, not a plain average of district percentages. Small UTs (Delhi, Chandigarh, Goa, Puducherry, Lakshadweep, Dadra and Nagar Haveli and Daman and Diu) are too small to tap as shapes, so they also get a clickable dot.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 (Create React App), Recharts for charts, react-icons |
| Map | Custom SVG choropleth drawn from a GeoJSON file (no map library). Falls back to a tile-grid map if the file can't load. |
| Backend | FastAPI (Python 3.12), served as a Vercel Python function |
| Language understanding | Google Gemini free tier, with a rule-based parser as the offline fallback |
| Data | Plain CSV loaded into memory once (no database) |
| Deployment | Vercel (frontend and `/api/*` on one domain) |
| CI | GitHub Actions (pytest + frontend tests and build) |

## Project structure

```
INGRES-Chatbot/
├── api/
│   └── index.py              Vercel entrypoint (exports the ASGI app)
├── ingres/                   Backend package
│   ├── app.py                FastAPI routes
│   ├── service.py            Builds answers, cards, charts, suggestions
│   ├── nlu.py                Intent schema, validation, offline rule parser
│   ├── gemini.py             Gemini client with fallback model and cooldown
│   ├── locations.py          Place-name index with fuzzy matching
│   ├── data.py               CSV loader, category thresholds, state aggregates
│   ├── geo.py                Tile-grid layout (map fallback)
│   └── data/
│       └── groundwater.csv   Generated dataset
├── scripts/
│   └── build_dataset.py      xlsx -> csv (only needed if the data changes)
├── data/source/
│   └── ingres-data.xlsx      Original CGWB export
├── frontend/
│   ├── public/
│   │   ├── index.html
│   │   └── india-states.geojson   State boundaries for the map
│   └── src/
│       ├── App.jsx, App.css, api.js, utils.js, index.js
│       └── components/
│           ├── ChatWindow.jsx     Chat loop, welcome map, voice
│           ├── MessageBubble.jsx
│           ├── ChartDisplay.jsx   Bar / pie / comparison / map charts
│           ├── GeoMap.jsx         India map (SVG from GeoJSON)
│           ├── TileMap.jsx        Tile-grid fallback map
│           ├── DataCard.jsx
│           ├── Sidebar.jsx        Language, quick questions, state list
│           └── InputBar.jsx
├── tests/                    Backend unit and API tests
├── .github/workflows/ci.yml  CI
├── vercel.json               Build and routing config
├── requirements.txt          Runtime dependencies
├── requirements-dev.txt      + pytest, uvicorn, pandas, openpyxl
└── .env.example              Environment variable template
```

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat` | Main chat endpoint (message in, answer + cards + charts out) |
| GET | `/api/states` | List of states and UTs |
| GET | `/api/districts/{state}` | Districts of a state |
| GET | `/api/data/{state}` | Data for a state |
| GET | `/api/stats/total` | All-India totals |
| GET | `/api/stats/{state}` | State summary |
| GET | `/api/map` | Map data: one entry per state with its category |
| GET | `/api/rankings` | Ranked states or districts |
| GET | `/api/health` | Health check, shows whether Gemini is configured |

## Prompts to try

**Lookups**
- `Rainfall in Bengaluru`
- `Groundwater extraction in Rajasthan`
- `Recharge in Tamil Nadu`
- `India overview`

**Rankings**
- `Top 5 states by groundwater extraction`
- `Lowest rainfall states`
- `Most over-exploited districts in Punjab`
- `Which are the driest districts in Rajasthan?`

**Comparisons and counts**
- `Compare Karnataka and Kerala`
- `Compare Bengaluru (Urban) and Kolar`
- `How many districts are over-exploited in India?`

**Follow-ups** (ask these right after a lookup)
- `what about net availability?`
- `and its recharge?` (most reliable with a Gemini key; the offline parser may answer for all of India instead)

**Typos**
- `rainfall in Banglore`

**Other languages** (need a Gemini key, see below)
- `दिल्ली में बारिश कितनी है?` (Hindi)
- `ಬೆಂಗಳೂರಿನಲ್ಲಿ ಮಳೆ` (Kannada)

**Or just tap any state on the map.**

> **Without a Gemini key** the offline parser handles the English prompts above (lookups, rankings, comparisons, counts, simple follow-ups and typos). It does **not** recognise place names written in Hindi, Kannada or the other scripts: those questions fall back to the all-India overview. **With a key**, Gemini translates the question and place names, and free-form phrasing works much better.


## Run locally

```bash
# Backend (from the project root)
pip install -r requirements-dev.txt
uvicorn api.index:app --port 8000 --reload

# Frontend (second terminal)
cd frontend
npm install
npm start          # http://localhost:3000, proxies /api to :8000
```

## Tests

```bash
# Backend (60 tests; the HTTP tests need fastapi installed)
python -m pytest -q

# Frontend utilities
cd frontend && npm test
```

The tests cover data loading and category thresholds, place-name matching, the offline NLU parser, Gemini output sanitising and fallback behaviour, the chat service, and the API routes (including a regression test for route order).

Vercel doesn't run tests itself. `.github/workflows/ci.yml` runs the backend tests, the frontend tests and a production build on every push and pull request.


## Design notes

- **No database.** The CSV (about 726 rows) is loaded once and indexed in memory, so cold starts are fast and there is nothing to host.
- **Never trust model output.** Gemini's reply is clamped to a fixed schema (allowed intents, metrics, categories and limits) before the service uses it.
- **Always an answer.** If Gemini is unavailable, a small rule-based parser takes over.
- **Weighted state values.** State stage and rainfall are weighted by district data, not simple averages.
- **Districts with no reported resource** are shown as "No data".

## Data and credits

Groundwater data: Central Ground Water Board (CGWB) / INGRES, 2024-25 assessment. State boundaries: see the source of your `india-states.geojson` file and check its licence before publishing.
