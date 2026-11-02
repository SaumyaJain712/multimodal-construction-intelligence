# ConstructAI — Requirements Specification

**Project:** Multimodal Construction Intelligence Platform
**UI brand:** ConstructAI
**Context:** Indian construction industry (₹ INR, Indian Standards / NBC 2016, plus OSHA 29 CFR 1926 for safety)

---

## 1. Purpose and scope

ConstructAI gives site engineers, contractors, safety officers and property buyers one web app with eight
AI tools. Users submit text, form fields and (for two tools) site photos. A single centralized AI layer sends
each request to a Groq-hosted vision-language model and always returns a complete, typed JSON response
that the React UI renders.

## 2. Functional requirements

| ID | Requirement |
|----|-------------|
| FR-1 | **Safety Monitor** — accept a site description (required), an optional site photo and an optional supporting document (only its filename is used); return risk level, hazards, missing / recommended PPE, OSHA + IS standards, corrective actions and a summary. |
| FR-2 | **Crack Detection** — accept a crack description and/or photo; classify crack type and severity; return probable causes, risks, repair methods, preventive measures and a summary. |
| FR-3 | **Real Estate Valuation** — accept location, area, property type, building age and amenities; return a value range, price per sq ft, monthly rent, rental ROI, appreciation outlook and key factors in INR. |
| FR-4 | **Project Planner** — accept a free-text project description (plot size, construction type, city); return material quantities, cost breakdown, total cost, phase timeline and a visualization prompt rendered as an image. |
| FR-5 | **Knowledge Base** — three modes: *Explain Concept*, *IS Codes & Standards*, *Generate Document*; return title, content, key points and references. |
| FR-6 | **Construction Chatbot** — conversational Q&A with history sent on every request; return a reply and clickable follow-up suggestions. |
| FR-7 | **Daily Site Assistant** — accept activity, labour count and site condition; return tasks, materials/equipment, safety checks and risk alerts. |
| FR-8 | **Weather Advisor** — accept activity, weather type and optional location; when a location is given, fetch live weather from Open-Meteo (no key); return PROCEED / PROCEED WITH CAUTION / POSTPONE with risks, precautions and mitigation steps. |
| FR-9 | **Health check** — report service status, configured model and whether the API key is configured. |
| FR-10 | **Dashboard** — a home page with cards linking to all eight modules; persistent sidebar navigation. |

## 3. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | **Schema guarantee** — every AI endpoint always returns every key of its schema with the correct type (lists stay lists, numbers stay numbers), even when the model returns partial, fenced or malformed JSON. |
| NFR-2 | **Resilience** — invalid AI output or a Groq error is retried once; after that the endpoint returns HTTP 200 with the default shape plus an `error` message. The UI never crashes on missing fields. |
| NFR-3 | **Input validation** — wrong file type, image > 4 MB, corrupt image, empty/whitespace text, or invalid enum values return HTTP 400 with a clear message. Numeric strings such as `"12"` are accepted for numeric fields. |
| NFR-4 | **Security** — the Groq API key is read only from the environment; it is never committed or sent to the browser. A missing key never crashes the app at import time. |
| NFR-5 | **Performance** — images are re-encoded to JPEG with a maximum side of 1600 px before being sent to the model; the AI call uses `temperature=0.2` and JSON mode. |
| NFR-6 | **Usability** — responsive layout (sidebar collapses to a top bar under 900 px), loading spinners, empty states, visible error messages, colored risk badges and ₹ formatting with Indian digit grouping. |
| NFR-7 | **Deployability** — one Vercel project serves the static Vite build and the FastAPI app as a Python serverless function under `/api`; SPA deep links fall back to `index.html`. |
| NFR-8 | **Testability** — the Groq client is injectable so the full API can be tested offline with pytest. |
| NFR-9 | **Disclaimer** — every page shows: "AI-generated insights are indicative and not a substitute for professional engineering advice." |

## 4. Input / output format per feature

All JSON responses may additionally contain `"error": "<message>"` when the AI step failed (HTTP 200).

### 4.1 `POST /api/safety-monitor` (multipart/form-data)

| Input | Type | Required |
|-------|------|----------|
| `text` | string | yes |
| `image` | JPG / PNG / WEBP ≤ 4 MB | no |
| `document` | any file (filename recorded only) | no |

```json
{ "risk_level": "Low|Medium|High|Critical", "hazards": [""], "missing_ppe": [""], "recommended_ppe": [""],
  "osha_standards": [""], "corrective_actions": [""], "summary": "" }
```

### 4.2 `POST /api/crack-detection` (multipart/form-data)

| Input | Type | Required |
|-------|------|----------|
| `text` | string | yes, unless an image is supplied |
| `image` | JPG / PNG / WEBP ≤ 4 MB | no |

```json
{ "crack_type": "Hairline|Vertical|Horizontal|Diagonal|Structural|None", "severity": "Minor|Moderate|Severe",
  "probable_causes": [""], "potential_risks": [""], "repair_methods": [""], "preventive_measures": [""], "summary": "" }
```

### 4.3 `POST /api/real-estate-valuation` (multipart/form-data)

| Input | Type | Required |
|-------|------|----------|
| `location` | string | yes |
| `area` | number (sq ft) as string | yes, > 0 |
| `property_type` | `Residential` \| `Commercial` \| `Plot` | default `Residential` |
| `building_age` | years | no |
| `amenities` | string | no |

```json
{ "estimated_value_min": 0, "estimated_value_max": 0, "price_per_sqft": 0, "rental_income_monthly": 0,
  "roi_percent": 0, "appreciation_outlook": "", "key_factors": [""], "currency": "INR", "disclaimer": "" }
```

### 4.4 `POST /api/project-planner` (JSON)

Input: `{ "description": "G+1 house, 1500 sq ft, RCC frame, Pune" }`

```json
{ "materials": { "cement_bags": 0, "sand_cft": 0, "aggregate_cft": 0, "steel_kg": 0, "bricks": 0 },
  "cost_breakdown": [{ "category": "", "amount": 0 }], "total_cost": 0,
  "timeline": [{ "phase": "", "duration_weeks": 0, "tasks": [""] }], "visualization_prompt": "" }
```

The UI renders `visualization_prompt` via `https://image.pollinations.ai/prompt/{prompt}?width=768&height=512&nologo=true`
and falls back to showing the prompt text if the image fails.

### 4.5 `POST /api/knowledge-base` (JSON)

Input: `{ "query": "...", "mode": "explain" | "standards" | "document" }`

```json
{ "title": "", "content": "", "key_points": [""], "references": [""] }
```

### 4.6 `POST /api/chatbot` (JSON)

Input: `{ "query": "...", "history": [{ "role": "user|assistant", "text": "..." }] }` (last 10 turns used)

```json
{ "reply": "", "action_suggestions": [""] }
```

### 4.7 `POST /api/site-assistant` (JSON)

Input: `{ "activity": "...", "labour_count": 20, "site_condition": "..." }` (`labour_count` may be a numeric string)

```json
{ "tasks": [""], "materials_equipment": [""], "safety_checks": [""], "risk_alerts": [""] }
```

### 4.8 `POST /api/weather-advisor` (JSON)

Input: `{ "activity": "...", "weather": "Sunny|Rainy|Windy|Extreme Heat|Cold|Humid", "location": "Mumbai" }` (`location` optional)

```json
{ "decision": "PROCEED|PROCEED WITH CAUTION|POSTPONE", "identified_risks": [""], "precautions": [""],
  "mitigation_steps": [""], "live_weather": "present only when live data was fetched" }
```

### 4.9 `GET /api/health`

```json
{ "status": "ok", "model": "qwen/qwen3.8-27b", "key_configured": true }
```

## 5. Environment

| Variable | Purpose | Default |
|----------|---------|---------|
| `GROQ_API_KEY` | Groq API key (server side only) | — (required) |
| `GROQ_MODEL` | Groq model ID, must support vision + JSON mode | `qwen/qwen3.8-27b` |
| `VITE_API_URL` | Frontend API base URL (build time) | empty → relative `/api` |

> The original target model `meta-llama/llama-4-scout-17b-16e-instruct` has been decommissioned on Groq
> (returns `model_not_found`). `qwen/qwen3.8-27b` is the current vision-capable model and is the default.
