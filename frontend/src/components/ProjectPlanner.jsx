import { useState } from "react";
import { ClipboardList, ImageOff, Loader2, Sparkles } from "lucide-react";
import api, { errorMessage, formatINR } from "../api.js";
import { ModuleLayout, Page } from "./common.jsx";

const DEFAULT = {
  materials: { cement_bags: 0, sand_cft: 0, aggregate_cft: 0, steel_kg: 0, bricks: 0 },
  cost_breakdown: [], total_cost: 0, timeline: [], visualization_prompt: "",
};

const MATERIAL_ROWS = [
  ["cement_bags", "Cement", "bags (50 kg)"],
  ["sand_cft", "Sand", "cft"],
  ["aggregate_cft", "Aggregate", "cft"],
  ["steel_kg", "Steel (TMT)", "kg"],
  ["bricks", "Bricks", "nos"],
];

function Visualization({ prompt }) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  if (!prompt) return null;
  const src = `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=768&height=512&nologo=true`;
  return (
    <div className="viz-card">
      {!failed ? (
        <>
          {!loaded && (
            <div className="viz-loading"><Loader2 className="spin" size={22} /> Generating concept render…</div>
          )}
          <img src={src} alt={prompt} onLoad={() => setLoaded(true)} onError={() => setFailed(true)}
            style={loaded ? undefined : { display: "none" }} />
        </>
      ) : (
        <div className="empty-state" style={{ padding: 24 }}><ImageOff size={28} /><p>Rendering unavailable</p></div>
      )}
      <div className="viz-prompt">“{prompt}”</div>
    </div>
  );
}

export default function ProjectPlanner() {
  const [description, setDescription] = useState("");
  const [data, setData] = useState(DEFAULT);
  const [hasResult, setHasResult] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!description.trim()) return setError("Please describe the project.");
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/project-planner", { description });
      setData({ ...DEFAULT, ...res.data, materials: { ...DEFAULT.materials, ...(res.data?.materials || {}) } });
      setHasResult(true);
      if (res.data?.error) setError(res.data.error);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const materials = data?.materials || DEFAULT.materials;

  return (
    <Page title="Project Planner" subtitle="Quantities, costs and schedule from a plain-English project brief.">
      <ModuleLayout
        loading={loading} error={error} hasResult={hasResult}
        emptyIcon={ClipboardList} emptyText="Describe plot size, construction type and city to generate a project plan."
        form={
          <form className="form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="p-desc">Project description *</label>
              <textarea id="p-desc" value={description} onChange={(e) => setDescription(e.target.value)} style={{ minHeight: 160 }}
                placeholder="e.g. G+1 independent house on a 30x40 ft plot, 2400 sq ft built-up, RCC frame with brick walls, standard finishes, in Jaipur" />
            </div>
            <button className="btn" disabled={loading}>
              <Sparkles size={18} /> {loading ? "Planning…" : "Generate Plan"}
            </button>
          </form>
        }
      >
        <div className="result-head">
          <h3>Project Plan</h3>
          <span className="badge badge-amber">Total {formatINR(data?.total_cost)}</span>
        </div>

        <h4 className="section-title">Material estimate</h4>
        <table>
          <thead><tr><th>Material</th><th className="num">Quantity</th><th>Unit</th></tr></thead>
          <tbody>
            {MATERIAL_ROWS.map(([key, label, unit]) => (
              <tr key={key}>
                <td>{label}</td>
                <td className="num">{Math.round(Number(materials[key]) || 0).toLocaleString("en-IN")}</td>
                <td>{unit}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h4 className="section-title">Cost breakdown</h4>
        <table>
          <thead><tr><th>Category</th><th className="num">Amount</th></tr></thead>
          <tbody>
            {(data?.cost_breakdown || []).map((row, i) => (
              <tr key={i}><td>{row?.category}</td><td className="num">{formatINR(row?.amount)}</td></tr>
            ))}
            <tr className="total"><td>Total</td><td className="num">{formatINR(data?.total_cost)}</td></tr>
          </tbody>
        </table>

        <h4 className="section-title">Timeline</h4>
        <ul className="timeline">
          {(data?.timeline || []).map((phase, i) => (
            <li key={i}>
              <span className="phase">{phase?.phase}</span>
              <span className="weeks">{Number(phase?.duration_weeks) || 0} weeks</span>
              <ul>{(phase?.tasks || []).map((t, j) => <li key={j}>{t}</li>)}</ul>
            </li>
          ))}
        </ul>

        {data?.visualization_prompt && (
          <>
            <h4 className="section-title">Concept visualization</h4>
            <Visualization key={data.visualization_prompt} prompt={data.visualization_prompt} />
          </>
        )}
      </ModuleLayout>
    </Page>
  );
}
