"""ConstructAI — Multimodal Construction Intelligence Platform (FastAPI backend).

All eight features share one centralized AI layer (`query_ai`) that talks to Groq,
enforces each feature's JSON schema, and always returns a complete response shape.
"""
import asyncio
import base64
import copy
import io
import json
import logging
import os
import re
from typing import Annotated, Any, List, Literal, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import AfterValidator, BaseModel, Field, ValidationError

load_dotenv()

logger = logging.getLogger("constructai")

# Llama 4 Scout was decommissioned on Groq; Qwen 3.8 27B is the current vision-capable model.
DEFAULT_MODEL = "qwen/qwen3.8-27b"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGE_SIDE = 1600


def get_model() -> str:
    return os.getenv("GROQ_MODEL") or DEFAULT_MODEL


def get_client():
    """Create the Groq client lazily so a missing key never crashes the app at import time."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    from groq import AsyncGroq

    return AsyncGroq(api_key=api_key, timeout=55.0)


app = FastAPI(title="ConstructAI — Multimodal Construction Intelligence API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are ConstructAI, a senior construction-domain expert (civil/structural engineer,
site safety officer, quantity surveyor, and Indian real-estate analyst) working in the Indian context.

GENERAL RULES
- All money is in Indian Rupees (INR, ₹). Give plain numbers (no symbols, no commas) in numeric fields.
- Reference Indian standards where relevant: IS 456 (plain & reinforced concrete), IS 800 (steel),
  IS 875 (loads), IS 1893 (seismic), IS 13920 (ductile detailing), IS 3370 (water-retaining structures),
  National Building Code of India (NBC 2016), IS 3764 (excavation safety), IS 4130 (demolition safety),
  IS 2925 (helmets), IS 3521 (safety belts/harness), BOCW Act 1996. For safety, also cite OSHA 29 CFR 1926.
- Be specific, practical and conservative. When unsure, say so and recommend a qualified engineer.
- An image may be attached. Base observations on what is actually visible; do not invent details.

FEATURE GUIDELINES AND EXACT JSON SCHEMAS

1. SAFETY_MONITOR — identify hazards (falls, electrical, excavation, scaffolding, struck-by, fire, housekeeping),
   missing PPE vs. required PPE, cite OSHA 1926 + Indian standards, give prioritised corrective actions.
{"risk_level": "Low|Medium|High|Critical", "hazards": [str], "missing_ppe": [str], "recommended_ppe": [str],
 "osha_standards": [str], "corrective_actions": [str], "summary": str}

2. CRACK_DETECTION — classify by pattern/orientation/width; structural if > 3mm, diagonal at openings,
   or indicating settlement/shear. Consider shrinkage, thermal movement, settlement, corrosion, overloading.
{"crack_type": "Hairline|Vertical|Horizontal|Diagonal|Structural|None", "severity": "Minor|Moderate|Severe",
 "probable_causes": [str], "potential_risks": [str], "repair_methods": [str], "preventive_measures": [str], "summary": str}

3. REAL_ESTATE_VALUATION — use realistic current Indian market rates for the city/locality, adjust for
   property type, age (depreciation), and amenities. Rental yield typically 2-4% residential, 6-9% commercial.
{"estimated_value_min": number, "estimated_value_max": number, "price_per_sqft": number,
 "rental_income_monthly": number, "roi_percent": number, "appreciation_outlook": str, "key_factors": [str],
 "currency": "INR", "disclaimer": str}

4. PROJECT_PLANNER — estimate quantities from built-up area using standard Indian thumb rules
   (approx. per sqft: cement 0.4 bags, sand 1.8 cft, aggregate 1.35 cft, steel 4 kg, bricks 8 nos for RCC frame),
   current city construction rates, and realistic phase durations. visualization_prompt is a vivid one-sentence
   architectural rendering prompt of the finished building.
{"materials": {"cement_bags": number, "sand_cft": number, "aggregate_cft": number, "steel_kg": number, "bricks": number},
 "cost_breakdown": [{"category": str, "amount": number}], "total_cost": number,
 "timeline": [{"phase": str, "duration_weeks": number, "tasks": [str]}], "visualization_prompt": str}

5. KNOWLEDGE_BASE — mode "explain": teach the concept clearly with examples; mode "standards": explain the
   relevant IS codes/NBC clauses and what they require; mode "document": draft the requested document
   (method statement, checklist, letter, report) in full in "content" using plain text with line breaks.
{"title": str, "content": str, "key_points": [str], "references": [str]}

6. CHATBOT — friendly, concise construction assistant; use conversation history for context.
{"reply": str, "action_suggestions": [str]}   (action_suggestions: 2-4 short follow-up questions the user could ask)

7. SITE_ASSISTANT — a practical daily plan for the given activity, labour count and site condition.
{"tasks": [str], "materials_equipment": [str], "safety_checks": [str], "risk_alerts": [str]}

8. WEATHER_ADVISOR — decide whether the activity should proceed given the weather (and live weather data if
   supplied). Concrete pours in rain/extreme heat, crane/height work in wind > 30 km/h, etc. need care.
{"decision": "PROCEED|PROCEED WITH CAUTION|POSTPONE", "identified_risks": [str], "precautions": [str], "mitigation_steps": [str]}

Respond ONLY with valid JSON for the ACTIVATED FEATURE. No markdown, no extra text."""

# ---------------------------------------------------------------------------
# Pydantic schemas (response contracts) and defaults
# ---------------------------------------------------------------------------


class SafetyResult(BaseModel):
    risk_level: str = "Unknown"
    hazards: List[str] = []
    missing_ppe: List[str] = []
    recommended_ppe: List[str] = []
    osha_standards: List[str] = []
    corrective_actions: List[str] = []
    summary: str = ""


class CrackResult(BaseModel):
    crack_type: str = "None"
    severity: str = "Minor"
    probable_causes: List[str] = []
    potential_risks: List[str] = []
    repair_methods: List[str] = []
    preventive_measures: List[str] = []
    summary: str = ""


class ValuationResult(BaseModel):
    estimated_value_min: float = 0.0
    estimated_value_max: float = 0.0
    price_per_sqft: float = 0.0
    rental_income_monthly: float = 0.0
    roi_percent: float = 0.0
    appreciation_outlook: str = ""
    key_factors: List[str] = []
    currency: str = "INR"
    disclaimer: str = "Indicative AI estimate only. Consult a registered valuer before any transaction."


class Materials(BaseModel):
    cement_bags: float = 0.0
    sand_cft: float = 0.0
    aggregate_cft: float = 0.0
    steel_kg: float = 0.0
    bricks: float = 0.0


class CostItem(BaseModel):
    category: str = ""
    amount: float = 0.0


class TimelinePhase(BaseModel):
    phase: str = ""
    duration_weeks: float = 0.0
    tasks: List[str] = []


class PlannerResult(BaseModel):
    materials: Materials = Materials()
    cost_breakdown: List[CostItem] = []
    total_cost: float = 0.0
    timeline: List[TimelinePhase] = []
    visualization_prompt: str = ""


class KnowledgeResult(BaseModel):
    title: str = ""
    content: str = ""
    key_points: List[str] = []
    references: List[str] = []


class ChatResult(BaseModel):
    reply: str = ""
    action_suggestions: List[str] = []


class SiteResult(BaseModel):
    tasks: List[str] = []
    materials_equipment: List[str] = []
    safety_checks: List[str] = []
    risk_alerts: List[str] = []


class WeatherResult(BaseModel):
    decision: str = "PROCEED WITH CAUTION"
    identified_risks: List[str] = []
    precautions: List[str] = []
    mitigation_steps: List[str] = []


FEATURE_MODELS = {
    "SAFETY_MONITOR": SafetyResult,
    "CRACK_DETECTION": CrackResult,
    "REAL_ESTATE_VALUATION": ValuationResult,
    "PROJECT_PLANNER": PlannerResult,
    "KNOWLEDGE_BASE": KnowledgeResult,
    "CHATBOT": ChatResult,
    "SITE_ASSISTANT": SiteResult,
    "WEATHER_ADVISOR": WeatherResult,
}

# Templates describe the type of every key; list templates hold one item template.
TEMPLATES = {
    "SAFETY_MONITOR": {**SafetyResult().model_dump(), "hazards": [""], "missing_ppe": [""],
                       "recommended_ppe": [""], "osha_standards": [""], "corrective_actions": [""]},
    "CRACK_DETECTION": {**CrackResult().model_dump(), "probable_causes": [""], "potential_risks": [""],
                        "repair_methods": [""], "preventive_measures": [""]},
    "REAL_ESTATE_VALUATION": {**ValuationResult().model_dump(), "key_factors": [""]},
    "PROJECT_PLANNER": {
        **PlannerResult().model_dump(),
        "cost_breakdown": [{"category": "", "amount": 0.0}],
        "timeline": [{"phase": "", "duration_weeks": 0.0, "tasks": [""]}],
    },
    "KNOWLEDGE_BASE": {**KnowledgeResult().model_dump(), "key_points": [""], "references": [""]},
    "CHATBOT": {**ChatResult().model_dump(), "action_suggestions": [""]},
    "SITE_ASSISTANT": {k: [""] for k in SiteResult().model_dump()},
    "WEATHER_ADVISOR": {**WeatherResult().model_dump(), "identified_risks": [""], "precautions": [""],
                        "mitigation_steps": [""]},
}

DEFAULTS = {name: model().model_dump() for name, model in FEATURE_MODELS.items()}

ENUMS = {
    ("SAFETY_MONITOR", "risk_level"): ["Low", "Medium", "High", "Critical"],
    ("CRACK_DETECTION", "crack_type"): ["Hairline", "Vertical", "Horizontal", "Diagonal", "Structural", "None"],
    ("CRACK_DETECTION", "severity"): ["Minor", "Moderate", "Severe"],
    ("WEATHER_ADVISOR", "decision"): ["PROCEED", "PROCEED WITH CAUTION", "POSTPONE"],
}

# ---------------------------------------------------------------------------
# Coercion helpers — make AI output match the template's types exactly
# ---------------------------------------------------------------------------

_MISSING = object()


def _to_number(value: Any, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[₹,\s]|INR|Rs\.?", "", value)
        match = re.search(r"-?\d+(\.\d+)?", cleaned)
        if match:
            return float(match.group())
    return default


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return "; ".join(f"{k}: {_to_text(v)}" for k, v in value.items())
    if isinstance(value, list):
        return "; ".join(_to_text(v) for v in value)
    return str(value)


def coerce(template: Any, value: Any) -> Any:
    """Recursively coerce `value` into the shape of `template`; missing keys get empty defaults."""
    if isinstance(template, dict):
        src = value if isinstance(value, dict) else {}
        return {k: coerce(t, src.get(k, _MISSING)) for k, t in template.items()}
    if isinstance(template, list):
        item_t = template[0] if template else ""
        if value is _MISSING or value is None:
            return []
        if isinstance(value, str):
            value = [line for line in re.split(r"\n+", value) if line.strip()]
        if not isinstance(value, list):
            value = [value]
        out = [coerce(item_t, v) for v in value if v is not None]
        return [v for v in out if v != ""]
    if isinstance(template, (int, float)) and not isinstance(template, bool):
        return template if value is _MISSING else _to_number(value, template)
    # string
    if value is _MISSING or value is None:
        return template
    return _to_text(value) or template


def normalize_enums(feature: str, data: dict) -> dict:
    for (feat, key), allowed in ENUMS.items():
        if feat != feature:
            continue
        raw = str(data.get(key, "")).strip().upper().replace("_", " ")
        match = next((a for a in allowed if a.upper() == raw), None)
        if match is None:
            match = next((a for a in allowed if a.upper() in raw), None)
        data[key] = match or DEFAULTS[feature][key]
    return data


def parse_ai_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("AI response is not a JSON object")
    return data


def build_result(feature: str, data: dict) -> dict:
    merged = normalize_enums(feature, coerce(TEMPLATES[feature], data))
    return FEATURE_MODELS[feature].model_validate(merged).model_dump()


def default_with_error(feature: str, message: str) -> dict:
    return {**copy.deepcopy(DEFAULTS[feature]), "error": message}


# ---------------------------------------------------------------------------
# Image handling
# ---------------------------------------------------------------------------


async def encode_image(upload: UploadFile) -> str:
    """Validate an uploaded image and return it as base64 JPEG. Raises HTTP 400 on bad input."""
    name = (upload.filename or "").lower()
    ext = os.path.splitext(name)[1]
    ctype = (upload.content_type or "").lower()
    if ext not in ALLOWED_IMAGE_EXTS and ctype not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Unsupported image type. Please upload a JPG, PNG or WEBP image.")
    raw = await upload.read()
    if not raw:
        raise HTTPException(400, "The uploaded image is empty.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image is too large. Maximum size is 4 MB.")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "The uploaded image is corrupt or unreadable.")
    if img.format not in {"JPEG", "PNG", "WEBP"}:
        raise HTTPException(400, "Unsupported image type. Please upload a JPG, PNG or WEBP image.")
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def has_file(upload: Optional[UploadFile]) -> bool:
    return upload is not None and bool(getattr(upload, "filename", ""))


# ---------------------------------------------------------------------------
# Centralized AI layer
# ---------------------------------------------------------------------------


def _friendly_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "model" in text and ("not found" in text or "decommissioned" in text or "does not exist" in text):
        return f"The configured AI model ({get_model()}) is unavailable. Please update GROQ_MODEL."
    if "rate" in text and "limit" in text:
        return "The AI service is busy (rate limit reached). Please retry in a minute."
    if "auth" in text or "api key" in text or "401" in text:
        return "The AI service rejected the API key. Please check GROQ_API_KEY."
    if "timeout" in text or "timed out" in text:
        return "The AI service timed out. Please retry."
    return "The AI service could not produce a valid response. Please retry."


async def query_ai(feature: str, user_inputs: dict, image_file: Optional[str] = None) -> dict:
    """Send one feature request to Groq and return a schema-complete dict (never raises for AI errors).

    `image_file` is a base64 JPEG string produced by `encode_image`.
    """
    client = get_client()
    if client is None:
        return default_with_error(feature, "GROQ_API_KEY is not configured on the server.")

    lines = "\n".join(f"{k}: {v}" for k, v in user_inputs.items() if v not in (None, ""))
    text = f"ACTIVATE FEATURE: {feature}\nINPUT DATA:\n{lines}"
    if image_file:
        content: Any = [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_file}"}},
        ]
    else:
        content = text
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}]

    last_error: Exception = RuntimeError("unknown error")
    for attempt in range(2):
        try:
            completion = await client.chat.completions.create(
                model=get_model(),
                messages=messages,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content
            return build_result(feature, parse_ai_json(raw))
        except (json.JSONDecodeError, ValueError, ValidationError, TypeError, AttributeError, IndexError) as exc:
            last_error = exc
            logger.warning("%s: invalid AI output on attempt %d: %s", feature, attempt + 1, exc)
        except Exception as exc:  # Groq/network errors
            last_error = exc
            logger.warning("%s: AI call failed on attempt %d: %s", feature, attempt + 1, exc)
    return default_with_error(feature, _friendly_error(last_error))


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


def _not_blank(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("must not be empty")
    return value.strip()


NonBlank = Annotated[str, AfterValidator(_not_blank)]


class PlannerRequest(BaseModel):
    description: NonBlank


class KnowledgeRequest(BaseModel):
    query: NonBlank
    mode: Literal["explain", "standards", "document"] = "explain"


class ChatTurn(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    query: NonBlank
    history: List[ChatTurn] = []


class SiteRequest(BaseModel):
    activity: NonBlank
    labour_count: int = Field(ge=0, le=100000)
    site_condition: str = ""


class WeatherRequest(BaseModel):
    activity: NonBlank
    weather: Literal["Sunny", "Rainy", "Windy", "Extreme Heat", "Cold", "Humid"]
    location: Optional[str] = None


def require_text(value: Optional[str], field: str) -> str:
    if value is None or not value.strip():
        raise HTTPException(400, f"'{field}' is required and cannot be empty.")
    return value.strip()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Report bad user input as HTTP 400 with a readable message."""
    problems = []
    for err in exc.errors():
        loc = list(err.get("loc", []))
        if loc and loc[0] in ("body", "query", "path", "header"):
            loc = loc[1:]
        field = ".".join(str(p) for p in loc)
        problems.append(f"{field or 'request'}: {err.get('msg', 'invalid value')}")
    return JSONResponse(status_code=400, content={"detail": "Invalid input — " + "; ".join(problems)})


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": get_model(), "key_configured": bool(os.getenv("GROQ_API_KEY"))}


@app.post("/api/safety-monitor")
async def safety_monitor(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    document: Optional[UploadFile] = File(None),
):
    text = require_text(text, "text")
    image_b64 = await encode_image(image) if has_file(image) else None
    inputs = {"site_description": text}
    if has_file(document):
        inputs["attached_document"] = document.filename
    if image_b64:
        inputs["image"] = "site photo attached"
    return await query_ai("SAFETY_MONITOR", inputs, image_b64)


@app.post("/api/crack-detection")
async def crack_detection(text: Optional[str] = Form(None), image: Optional[UploadFile] = File(None)):
    image_b64 = await encode_image(image) if has_file(image) else None
    if not image_b64 and (text is None or not text.strip()):
        raise HTTPException(400, "Please describe the crack or upload a photo.")
    inputs = {"description": (text or "").strip() or "See attached photo"}
    if image_b64:
        inputs["image"] = "crack photo attached"
    return await query_ai("CRACK_DETECTION", inputs, image_b64)


@app.post("/api/real-estate-valuation")
async def real_estate_valuation(
    location: Optional[str] = Form(None),
    area: Optional[str] = Form(None),
    property_type: str = Form("Residential"),
    building_age: Optional[str] = Form("0"),
    amenities: Optional[str] = Form(""),
):
    location = require_text(location, "location")
    area = require_text(area, "area")
    if _to_number(area, -1) <= 0:
        raise HTTPException(400, "'area' must be a positive number of square feet.")
    if property_type not in {"Residential", "Commercial", "Plot"}:
        raise HTTPException(400, "'property_type' must be Residential, Commercial or Plot.")
    result = await query_ai(
        "REAL_ESTATE_VALUATION",
        {
            "location": location,
            "area_sqft": area,
            "property_type": property_type,
            "building_age_years": building_age or "0",
            "amenities": amenities or "none specified",
        },
    )
    result["currency"] = "INR"
    return result


@app.post("/api/project-planner")
async def project_planner(req: PlannerRequest):
    return await query_ai("PROJECT_PLANNER", {"project_description": req.description})


@app.post("/api/knowledge-base")
async def knowledge_base(req: KnowledgeRequest):
    return await query_ai("KNOWLEDGE_BASE", {"mode": req.mode, "query": req.query})


@app.post("/api/chatbot")
async def chatbot(req: ChatRequest):
    history = "\n".join(f"{t.role}: {t.text}" for t in req.history[-10:])
    return await query_ai("CHATBOT", {"conversation_history": history or "(none)", "user_message": req.query})


@app.post("/api/site-assistant")
async def site_assistant(req: SiteRequest):
    return await query_ai(
        "SITE_ASSISTANT",
        {"activity": req.activity, "labour_count": req.labour_count, "site_condition": req.site_condition or "normal"},
    )


def fetch_live_weather(location: str) -> Optional[str]:
    """Look up current weather from Open-Meteo (no API key). Returns a summary string or None."""
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1},
            timeout=5,
        ).json()
        place = (geo.get("results") or [None])[0]
        if not place:
            return None
        cur = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            },
            timeout=5,
        ).json()["current"]
        return (
            f"{place.get('name')}, {place.get('country', '')}: {cur['temperature_2m']}°C, "
            f"humidity {cur['relative_humidity_2m']}%, precipitation {cur['precipitation']} mm, "
            f"wind {cur['wind_speed_10m']} km/h, WMO weather code {cur['weather_code']}"
        )
    except Exception as exc:
        logger.info("Live weather lookup failed: %s", exc)
        return None


@app.post("/api/weather-advisor")
async def weather_advisor(req: WeatherRequest):
    inputs = {"activity": req.activity, "weather": req.weather}
    if req.location and req.location.strip():
        inputs["location"] = req.location.strip()
        live = await asyncio.to_thread(fetch_live_weather, req.location.strip())
        if live:
            inputs["live_weather"] = live
    result = await query_ai("WEATHER_ADVISOR", inputs)
    if "live_weather" in inputs:
        result["live_weather"] = inputs["live_weather"]
    return result
