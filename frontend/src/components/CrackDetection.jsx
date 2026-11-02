import { useState } from "react";
import { Activity, AlertTriangle, Hammer, Search, ShieldCheck } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { Badge, ImageDrop, ListBlock, ModuleLayout, Page } from "./common.jsx";

const DEFAULT = {
  crack_type: "", severity: "", probable_causes: [], potential_risks: [],
  repair_methods: [], preventive_measures: [], summary: "",
};

export default function CrackDetection() {
  const [text, setText] = useState("");
  const [image, setImage] = useState(null);
  const [data, setData] = useState(DEFAULT);
  const [hasResult, setHasResult] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim() && !image) return setError("Describe the crack or upload a photo.");
    const form = new FormData();
    form.append("text", text);
    if (image) form.append("image", image);
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/crack-detection", form);
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
    <Page title="Crack Detection" subtitle="Classify structural cracks and get repair recommendations.">
      <ModuleLayout
        loading={loading} error={error} hasResult={hasResult}
        emptyIcon={Activity} emptyText="Upload a crack photo and/or describe its location, width and pattern."
        form={
          <form className="form" onSubmit={submit}>
            <ImageDrop file={image} onChange={setImage} onError={setError} label="Upload crack photo" />
            <div className="field">
              <label htmlFor="crack-text">Description</label>
              <textarea id="crack-text" value={text} onChange={(e) => setText(e.target.value)}
                placeholder="e.g. 2 mm diagonal crack from window corner on ground-floor brick wall, building 8 years old" />
            </div>
            <button className="btn" disabled={loading}>
              <Search size={18} /> {loading ? "Inspecting…" : "Analyze Crack"}
            </button>
          </form>
        }
      >
        <div className="result-head">
          <h3>Inspection Result</h3>
        </div>
        <div className="stats">
          <div className="stat"><div className="stat-label">Crack type</div><div className="stat-value"><Badge value={data?.crack_type} /></div></div>
          <div className="stat"><div className="stat-label">Severity</div><div className="stat-value"><Badge value={data?.severity} /></div></div>
        </div>
        {data?.summary && <p className="summary">{data.summary}</p>}
        <ListBlock title="Probable causes" items={data?.probable_causes || []} icon={Search} />
        <ListBlock title="Potential risks" items={data?.potential_risks || []} icon={AlertTriangle} />
        <ListBlock title="Repair methods" items={data?.repair_methods || []} icon={Hammer} />
        <ListBlock title="Preventive measures" items={data?.preventive_measures || []} icon={ShieldCheck} />
      </ModuleLayout>
    </Page>
  );
}
