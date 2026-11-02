import { useState } from "react";
import { Building2, Calculator, TrendingUp } from "lucide-react";
import api, { errorMessage, formatINR } from "../api.js";
import { ListBlock, ModuleLayout, Page } from "./common.jsx";

const DEFAULT = {
  estimated_value_min: 0, estimated_value_max: 0, price_per_sqft: 0, rental_income_monthly: 0,
  roi_percent: 0, appreciation_outlook: "", key_factors: [], currency: "INR", disclaimer: "",
};

export default function Valuation() {
  const [form, setForm] = useState({ location: "", area: "", property_type: "Residential", building_age: "", amenities: "" });
  const [data, setData] = useState(DEFAULT);
  const [hasResult, setHasResult] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.location.trim()) return setError("Please enter a location.");
    if (!(Number(form.area) > 0)) return setError("Please enter a valid area in sq ft.");
    const body = new FormData();
    Object.entries(form).forEach(([k, v]) => body.append(k, k === "building_age" ? v || "0" : v));
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/real-estate-valuation", body);
      setData({ ...DEFAULT, ...res.data });
      setHasResult(true);
      if (res.data?.error) setError(res.data.error);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const roi = Number(data?.roi_percent) || 0;

  return (
    <Page title="Real Estate Valuation" subtitle="AI-assisted property valuation for Indian markets.">
      <ModuleLayout
        loading={loading} error={error} hasResult={hasResult}
        emptyIcon={Building2} emptyText="Enter property details to estimate its market value, rent and ROI."
        form={
          <form className="form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="v-loc">Location *</label>
              <input id="v-loc" value={form.location} onChange={set("location")} placeholder="e.g. Whitefield, Bengaluru" />
            </div>
            <div className="row-2">
              <div className="field">
                <label htmlFor="v-area">Area (sq ft) *</label>
                <input id="v-area" type="number" min="1" value={form.area} onChange={set("area")} placeholder="1200" />
              </div>
              <div className="field">
                <label htmlFor="v-age">Building age (years)</label>
                <input id="v-age" type="number" min="0" value={form.building_age} onChange={set("building_age")} placeholder="5" />
              </div>
            </div>
            <div className="field">
              <label htmlFor="v-type">Property type</label>
              <select id="v-type" value={form.property_type} onChange={set("property_type")}>
                <option>Residential</option>
                <option>Commercial</option>
                <option>Plot</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="v-amen">Amenities</label>
              <textarea id="v-amen" value={form.amenities} onChange={set("amenities")}
                placeholder="e.g. Gym, swimming pool, covered parking, 24x7 security, near metro" />
            </div>
            <button className="btn" disabled={loading}>
              <Calculator size={18} /> {loading ? "Valuing…" : "Estimate Value"}
            </button>
          </form>
        }
      >
        <div className="result-head"><h3>Valuation Estimate</h3></div>
        <div className="stats">
          <div className="stat highlight" style={{ gridColumn: "1 / -1" }}>
            <div className="stat-label">Estimated market value</div>
            <div className="stat-value">
              {formatINR(data?.estimated_value_min)} – {formatINR(data?.estimated_value_max)}
            </div>
          </div>
          <div className="stat"><div className="stat-label">Price / sq ft</div><div className="stat-value">{formatINR(data?.price_per_sqft)}</div></div>
          <div className="stat"><div className="stat-label">Monthly rent</div><div className="stat-value">{formatINR(data?.rental_income_monthly)}</div></div>
          <div className="stat"><div className="stat-label">Rental ROI</div><div className="stat-value">{roi.toFixed(2)}%</div></div>
        </div>
        {data?.appreciation_outlook && (
          <p className="summary"><TrendingUp size={14} /> <strong>Outlook:</strong> {data.appreciation_outlook}</p>
        )}
        <ListBlock title="Key value factors" items={data?.key_factors || []} />
        {data?.disclaimer && <p className="hint">{data.disclaimer}</p>}
      </ModuleLayout>
    </Page>
  );
}
