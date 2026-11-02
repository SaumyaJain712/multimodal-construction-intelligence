import { useState } from "react";
import { AlertTriangle, BookMarked, CheckCircle2, FileText, HardHat, ShieldAlert, ShieldCheck, Wrench } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { Badge, ImageDrop, ListBlock, ModuleLayout, Page } from "./common.jsx";

const DEFAULT = {
  risk_level: "", hazards: [], missing_ppe: [], recommended_ppe: [],
  osha_standards: [], corrective_actions: [], summary: "",
};

export default function SafetyMonitor() {
  const [text, setText] = useState("");
  const [image, setImage] = useState(null);
  const [doc, setDoc] = useState(null);
  const [data, setData] = useState(DEFAULT);
  const [hasResult, setHasResult] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return setError("Please describe the site conditions.");
    const form = new FormData();
    form.append("text", text);
    if (image) form.append("image", image);
    if (doc) form.append("document", doc);
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/safety-monitor", form);
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
    <Page title="Safety Monitor" subtitle="Analyze site photos and descriptions for hazards and PPE compliance.">
      <ModuleLayout
        loading={loading} error={error} hasResult={hasResult}
        emptyIcon={ShieldAlert} emptyText="Describe the site and optionally upload a photo to run a safety audit."
        form={
          <form className="form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="safety-text">Site description *</label>
              <textarea id="safety-text" value={text} onChange={(e) => setText(e.target.value)}
                placeholder="e.g. 4 workers on 3rd floor slab edge fixing shuttering, no guardrails, one worker without helmet" />
            </div>
            <ImageDrop file={image} onChange={setImage} onError={setError} />
            <div className="field">
              <label htmlFor="safety-doc">Supporting document (optional)</label>
              <input id="safety-doc" type="file" onChange={(e) => setDoc(e.target.files?.[0] || null)} />
              <span className="hint">Only the file name is recorded for context.</span>
            </div>
            <button className="btn" disabled={loading}>
              <ShieldCheck size={18} /> {loading ? "Analyzing…" : "Run Safety Audit"}
            </button>
          </form>
        }
      >
        <div className="result-head">
          <h3>Safety Report</h3>
          <span>Risk level: <Badge value={data?.risk_level} /></span>
        </div>
        {data?.summary && <p className="summary">{data.summary}</p>}
        <ListBlock title="Hazards" items={data?.hazards || []} icon={AlertTriangle} />
        <ListBlock title="Missing PPE" items={data?.missing_ppe || []} icon={HardHat} />
        <ListBlock title="Recommended PPE" items={data?.recommended_ppe || []} icon={CheckCircle2} />
        <ListBlock title="Standards (OSHA / IS)" items={data?.osha_standards || []} icon={BookMarked} />
        <ListBlock title="Corrective actions" items={data?.corrective_actions || []} icon={Wrench} />
        {doc && <p className="hint"><FileText size={12} /> Document referenced: {doc.name}</p>}
      </ModuleLayout>
    </Page>
  );
}
