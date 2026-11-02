"""API tests for ConstructAI. The Groq client is always mocked — no network calls."""
import io
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import backend.main as main

client = TestClient(main.app)
REAL_FETCH_LIVE_WEATHER = main.fetch_live_weather


# ---------------------------------------------------------------------------
# Fake Groq client
# ---------------------------------------------------------------------------


class FakeCompletions:
    def __init__(self, responses):
        # Each response is a string (returned as message content) or an Exception (raised).
        self.responses = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))])


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


@pytest.fixture
def mock_ai(monkeypatch):
    """Install a fake Groq client returning the given responses; returns the fake for inspection."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def install(*responses):
        fake = FakeClient(responses)
        monkeypatch.setattr(main, "get_client", lambda: fake)
        return fake

    return install


@pytest.fixture(autouse=True)
def no_live_weather(monkeypatch):
    monkeypatch.setattr(main, "fetch_live_weather", lambda loc: None)


def image_bytes(fmt="PNG", size=(64, 64)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 120, 40)).save(buf, format=fmt)
    return buf.getvalue()


SAMPLE = {
    "SAFETY_MONITOR": {
        "risk_level": "High", "hazards": ["Unguarded edge"], "missing_ppe": ["Harness"],
        "recommended_ppe": ["Helmet", "Harness"], "osha_standards": ["29 CFR 1926.501"],
        "corrective_actions": ["Install guardrails"], "summary": "Fall risk at slab edge.",
    },
    "CRACK_DETECTION": {
        "crack_type": "Diagonal", "severity": "Moderate", "probable_causes": ["Differential settlement"],
        "potential_risks": ["Wall instability"], "repair_methods": ["Epoxy injection"],
        "preventive_measures": ["Improve drainage"], "summary": "Diagonal crack near window.",
    },
    "REAL_ESTATE_VALUATION": {
        "estimated_value_min": 9000000, "estimated_value_max": 11000000, "price_per_sqft": 8500,
        "rental_income_monthly": 28000, "roi_percent": 3.4, "appreciation_outlook": "Positive",
        "key_factors": ["Metro access"], "currency": "INR", "disclaimer": "Indicative only.",
    },
    "PROJECT_PLANNER": {
        "materials": {"cement_bags": 800, "sand_cft": 3600, "aggregate_cft": 2700, "steel_kg": 8000, "bricks": 16000},
        "cost_breakdown": [{"category": "Structure", "amount": 2500000}],
        "total_cost": 4500000,
        "timeline": [{"phase": "Foundation", "duration_weeks": 4, "tasks": ["Excavation"]}],
        "visualization_prompt": "Modern two-storey house in Pune",
    },
    "KNOWLEDGE_BASE": {"title": "Curing", "content": "Curing keeps concrete moist.", "key_points": ["7 days min"],
                       "references": ["IS 456:2000 Cl. 13.5"]},
    "CHATBOT": {"reply": "Use M20 for slabs.", "action_suggestions": ["What about M25?"]},
    "SITE_ASSISTANT": {"tasks": ["Formwork"], "materials_equipment": ["Plywood"], "safety_checks": ["Helmets"],
                       "risk_alerts": ["Rain forecast"]},
    "WEATHER_ADVISOR": {"decision": "POSTPONE", "identified_risks": ["Washout"], "precautions": ["Cover"],
                        "mitigation_steps": ["Reschedule"]},
}

# (feature, method, path, kwargs)
ENDPOINTS = [
    ("SAFETY_MONITOR", "/api/safety-monitor", {"data": {"text": "Workers on slab edge without harness"}}),
    ("CRACK_DETECTION", "/api/crack-detection", {"data": {"text": "Diagonal crack above window"}}),
    ("REAL_ESTATE_VALUATION", "/api/real-estate-valuation",
     {"data": {"location": "Baner, Pune", "area": "1200", "property_type": "Residential",
               "building_age": "5", "amenities": "Gym, pool"}}),
    ("PROJECT_PLANNER", "/api/project-planner", {"json": {"description": "G+1 house, 1500 sqft, RCC, Pune"}}),
    ("KNOWLEDGE_BASE", "/api/knowledge-base", {"json": {"query": "Concrete curing", "mode": "explain"}}),
    ("CHATBOT", "/api/chatbot", {"json": {"query": "Which grade for slabs?", "history": []}}),
    ("SITE_ASSISTANT", "/api/site-assistant",
     {"json": {"activity": "Slab casting", "labour_count": 20, "site_condition": "Dry"}}),
    ("WEATHER_ADVISOR", "/api/weather-advisor", {"json": {"activity": "Concrete pour", "weather": "Rainy"}}),
]


def assert_shape(feature, body):
    """Every default key is present with the same type as the default."""
    for key, default in main.DEFAULTS[feature].items():
        assert key in body, f"{feature} missing {key}"
        if isinstance(default, float):
            assert isinstance(body[key], (int, float)) and not isinstance(body[key], bool), key
        else:
            assert isinstance(body[key], type(default)), f"{feature}.{key} has type {type(body[key])}"


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_health(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["key_configured"] is True and body["model"]


@pytest.mark.parametrize("feature,path,kwargs", ENDPOINTS, ids=[e[0] for e in ENDPOINTS])
def test_endpoints_return_complete_schema(mock_ai, feature, path, kwargs):
    fake = mock_ai(json.dumps(SAMPLE[feature]))
    res = client.post(path, **kwargs)
    assert res.status_code == 200, res.text
    body = res.json()
    assert_shape(feature, body)
    assert "error" not in body
    call = fake.chat.completions.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert call["temperature"] == 0.2
    assert f"ACTIVATE FEATURE: {feature}" in call["messages"][1]["content"]


@pytest.mark.parametrize("feature,path,kwargs", ENDPOINTS, ids=[e[0] for e in ENDPOINTS])
def test_partial_ai_output_is_filled_with_defaults(mock_ai, feature, path, kwargs):
    mock_ai("{}")
    res = client.post(path, **kwargs)
    assert res.status_code == 200
    assert_shape(feature, res.json())


def test_safety_with_image_and_document(mock_ai):
    fake = mock_ai(json.dumps(SAMPLE["SAFETY_MONITOR"]))
    res = client.post(
        "/api/safety-monitor",
        data={"text": "Scaffold inspection"},
        files={"image": ("site.png", image_bytes(), "image/png"), "document": ("plan.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert res.status_code == 200
    assert res.json()["risk_level"] == "High"
    content = fake.chat.completions.calls[0]["messages"][1]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "plan.pdf" in content[0]["text"]


def test_crack_with_webp_image_only(mock_ai):
    mock_ai(json.dumps(SAMPLE["CRACK_DETECTION"]))
    res = client.post("/api/crack-detection", files={"image": ("c.webp", image_bytes("WEBP"), "image/webp")})
    assert res.status_code == 200
    assert res.json()["crack_type"] == "Diagonal"


def test_large_image_is_downscaled():
    from fastapi import UploadFile
    import asyncio, base64

    upload = UploadFile(io.BytesIO(image_bytes("JPEG", (3000, 2000))), filename="big.jpg",
                        headers={"content-type": "image/jpeg"})
    b64 = asyncio.run(main.encode_image(upload))
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    assert img.format == "JPEG" and max(img.size) == 1600


# ---------------------------------------------------------------------------
# Edge cases: bad user input -> HTTP 400
# ---------------------------------------------------------------------------


def test_no_image_is_fine(mock_ai):
    fake = mock_ai(json.dumps(SAMPLE["SAFETY_MONITOR"]))
    res = client.post("/api/safety-monitor", data={"text": "Excavation 3m deep, no shoring"})
    assert res.status_code == 200
    assert isinstance(fake.chat.completions.calls[0]["messages"][1]["content"], str)


def test_wrong_file_type(mock_ai):
    mock_ai("{}")
    res = client.post("/api/safety-monitor", data={"text": "x"}, files={"image": ("a.gif", b"GIF89a....", "image/gif")})
    assert res.status_code == 400
    assert "JPG, PNG or WEBP" in res.json()["detail"]


def test_text_file_disguised_as_image(mock_ai):
    mock_ai("{}")
    res = client.post("/api/crack-detection", data={"text": "x"}, files={"image": ("a.png", b"hello world", "image/png")})
    assert res.status_code == 400
    assert "corrupt" in res.json()["detail"]


def test_corrupt_image(mock_ai):
    mock_ai("{}")
    broken = image_bytes()[:40]
    res = client.post("/api/crack-detection", data={"text": "x"}, files={"image": ("a.png", broken, "image/png")})
    assert res.status_code == 400
    assert "corrupt" in res.json()["detail"]


def test_oversized_image(mock_ai):
    mock_ai("{}")
    big = b"\xff\xd8\xff" + b"0" * (4 * 1024 * 1024 + 10)
    res = client.post("/api/safety-monitor", data={"text": "x"}, files={"image": ("a.jpg", big, "image/jpeg")})
    assert res.status_code == 400
    assert "4 MB" in res.json()["detail"]


@pytest.mark.parametrize("text", ["", "   \n\t "])
def test_empty_or_whitespace_text_rejected(mock_ai, text):
    mock_ai("{}")
    assert client.post("/api/safety-monitor", data={"text": text}).status_code == 400
    assert client.post("/api/crack-detection", data={"text": text}).status_code == 400
    assert client.post("/api/chatbot", json={"query": text}).status_code == 400
    assert client.post("/api/project-planner", json={"description": text}).status_code == 400
    assert client.post("/api/knowledge-base", json={"query": text, "mode": "explain"}).status_code == 400
    assert client.post("/api/site-assistant", json={"activity": text, "labour_count": 5}).status_code == 400
    assert client.post("/api/weather-advisor", json={"activity": text, "weather": "Sunny"}).status_code == 400


def test_missing_safety_text():
    assert client.post("/api/safety-monitor", data={}).status_code == 400


def test_labour_count_as_string(mock_ai):
    fake = mock_ai(json.dumps(SAMPLE["SITE_ASSISTANT"]))
    res = client.post("/api/site-assistant", json={"activity": "Plastering", "labour_count": "12", "site_condition": "Wet"})
    assert res.status_code == 200
    assert "labour_count: 12" in fake.chat.completions.calls[0]["messages"][1]["content"]


def test_labour_count_not_a_number():
    res = client.post("/api/site-assistant", json={"activity": "Plastering", "labour_count": "twelve"})
    assert res.status_code == 400
    assert "labour_count" in res.json()["detail"]


def test_invalid_knowledge_mode():
    assert client.post("/api/knowledge-base", json={"query": "x", "mode": "poem"}).status_code == 400


def test_invalid_weather_value():
    assert client.post("/api/weather-advisor", json={"activity": "x", "weather": "Snowstorm"}).status_code == 400


def test_valuation_bad_area():
    res = client.post("/api/real-estate-valuation", data={"location": "Pune", "area": "abc", "property_type": "Plot"})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Edge cases: AI failures -> HTTP 200 with defaults + error
# ---------------------------------------------------------------------------


def test_malformed_ai_json_returns_defaults(mock_ai):
    fake = mock_ai("this is not json", "still {not json")
    res = client.post("/api/chatbot", json={"query": "hi"})
    assert res.status_code == 200
    body = res.json()
    assert_shape("CHATBOT", body)
    assert body["error"]
    assert len(fake.chat.completions.calls) == 2  # retried once


def test_malformed_then_valid_json_recovers(mock_ai):
    mock_ai("garbage", json.dumps(SAMPLE["CHATBOT"]))
    body = client.post("/api/chatbot", json={"query": "hi"}).json()
    assert body["reply"] == "Use M20 for slabs." and "error" not in body


def test_fenced_json_and_wrong_types_are_coerced(mock_ai):
    payload = {
        "materials": {"cement_bags": "800 bags", "steel_kg": "8,000"},
        "cost_breakdown": [{"category": "Structure", "amount": "₹25,00,000"}],
        "total_cost": "4500000",
        "timeline": [{"phase": "Foundation", "duration_weeks": "4", "tasks": "Excavation"}],
        "visualization_prompt": "House",
    }
    mock_ai("```json\n" + json.dumps(payload) + "\n```")
    body = client.post("/api/project-planner", json={"description": "house"}).json()
    assert body["materials"]["cement_bags"] == 800
    assert body["materials"]["steel_kg"] == 8000
    assert body["materials"]["bricks"] == 0
    assert body["cost_breakdown"][0]["amount"] == 2500000
    assert body["total_cost"] == 4500000
    assert body["timeline"][0]["tasks"] == ["Excavation"]


def test_enum_normalization(mock_ai):
    mock_ai(json.dumps({**SAMPLE["SAFETY_MONITOR"], "risk_level": "critical", "hazards": "Fall from height"}))
    body = client.post("/api/safety-monitor", data={"text": "x"}).json()
    assert body["risk_level"] == "Critical"
    assert body["hazards"] == ["Fall from height"]


def test_unknown_enum_falls_back_to_default(mock_ai):
    mock_ai(json.dumps({**SAMPLE["WEATHER_ADVISOR"], "decision": "maybe"}))
    body = client.post("/api/weather-advisor", json={"activity": "x", "weather": "Windy"}).json()
    assert body["decision"] == main.DEFAULTS["WEATHER_ADVISOR"]["decision"]


def test_groq_exception_returns_200_with_error(mock_ai):
    fake = mock_ai(RuntimeError("connection reset"))
    res = client.post("/api/site-assistant", json={"activity": "x", "labour_count": 3})
    assert res.status_code == 200
    body = res.json()
    assert_shape("SITE_ASSISTANT", body)
    assert "retry" in body["error"].lower()
    assert len(fake.chat.completions.calls) == 2


def test_model_not_found_message(mock_ai):
    mock_ai(Exception("Error code: 404 - model_not_found: The model does not exist"))
    body = client.post("/api/chatbot", json={"query": "hi"}).json()
    assert "GROQ_MODEL" in body["error"]


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert client.get("/api/health").json()["key_configured"] is False
    res = client.post("/api/chatbot", json={"query": "hi"})
    assert res.status_code == 200
    body = res.json()
    assert_shape("CHATBOT", body)
    assert "GROQ_API_KEY" in body["error"]


def test_weather_includes_live_data_when_available(mock_ai, monkeypatch):
    monkeypatch.setattr(main, "fetch_live_weather", lambda loc: "Mumbai: 31°C, wind 12 km/h")
    fake = mock_ai(json.dumps(SAMPLE["WEATHER_ADVISOR"]))
    body = client.post("/api/weather-advisor", json={"activity": "Pour", "weather": "Rainy", "location": "Mumbai"}).json()
    assert body["live_weather"].startswith("Mumbai")
    assert "live_weather: Mumbai" in fake.chat.completions.calls[0]["messages"][1]["content"]


def test_live_weather_failure_is_ignored(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("offline")

    monkeypatch.setattr(main.requests, "get", boom)
    assert REAL_FETCH_LIVE_WEATHER("Pune") is None


def test_chat_history_is_forwarded(mock_ai):
    fake = mock_ai(json.dumps(SAMPLE["CHATBOT"]))
    client.post("/api/chatbot", json={"query": "And for columns?",
                                      "history": [{"role": "user", "text": "Grade for slabs?"},
                                                  {"role": "assistant", "text": "M20"}]})
    content = fake.chat.completions.calls[0]["messages"][1]["content"]
    assert "user: Grade for slabs?" in content and "assistant: M20" in content
