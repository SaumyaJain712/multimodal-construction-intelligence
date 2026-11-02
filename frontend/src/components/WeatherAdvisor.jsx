import { useState } from "react";
import { AlertTriangle, CloudRain, ShieldCheck, Thermometer, Wrench } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { Badge, ListBlock, ModuleLayout, Page } from "./common.jsx";

const DEFAULT = { decision: "", identified_risks: [], precautions: [], mitigation_steps: [] };
const WEATHER = ["Sunny", "Rainy", "Windy", "Extreme Heat", "Cold", "Humid"];

export default function WeatherAdvisor() {
  const [form, setForm] = useState({ activity: "", weather: "Rainy", location: "" });
  const [data, setData] = useState(DEFAULT);
  const [hasResult, setHasResult] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.activity.trim()) return setError("Please enter the planned activity.");
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/weather-advisor", { ...form, location: form.location.trim() || null });
      setData({ ...DEFAULT, ...res.data });
      setHasResult(true);
      if (res.data?.error) setError(res.data.error);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page title="Weather Advisor" subtitle="Should today's work go ahead? Get a weather-aware decision.">
      <ModuleLayout
        loading={loading} error={error} hasResult={hasResult}
        emptyIcon={CloudRain} emptyText="Enter an activity and weather (add a city for live conditions) to get a go/no-go decision."
        form={
          <form className="form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="w-act">Planned activity *</label>
              <input id="w-act" value={form.activity} onChange={set("activity")} placeholder="e.g. Roof slab concreting" />
            </div>
            <div className="field">
              <label htmlFor="w-weather">Weather condition</label>
              <select id="w-weather" value={form.weather} onChange={set("weather")}>
                {WEATHER.map((w) => <option key={w}>{w}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="w-loc">Location (optional)</label>
              <input id="w-loc" value={form.location} onChange={set("location")} placeholder="e.g. Mumbai" />
              <span className="hint">If provided, live weather from Open-Meteo is included in the analysis.</span>
            </div>
            <button className="btn" disabled={loading}>
              <Thermometer size={18} /> {loading ? "Assessing…" : "Get Advice"}
            </button>
          </form>
        }
      >
        <div className="decision">Decision: <Badge value={data?.decision} /></div>
        {data?.live_weather && <div className="live-weather">Live weather — {data.live_weather}</div>}
        <ListBlock title="Identified risks" items={data?.identified_risks || []} icon={AlertTriangle} />
        <ListBlock title="Precautions" items={data?.precautions || []} icon={ShieldCheck} />
        <ListBlock title="Mitigation steps" items={data?.mitigation_steps || []} icon={Wrench} />
      </ModuleLayout>
    </Page>
  );
}
