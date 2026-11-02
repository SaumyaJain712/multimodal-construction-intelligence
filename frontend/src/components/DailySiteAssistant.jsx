import { useState } from "react";
import { AlertTriangle, Calendar, ClipboardCheck, ListChecks, Package } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { ListBlock, ModuleLayout, Page } from "./common.jsx";

const DEFAULT = { tasks: [], materials_equipment: [], safety_checks: [], risk_alerts: [] };

export default function DailySiteAssistant() {
  const [form, setForm] = useState({ activity: "", labour_count: "", site_condition: "" });
  const [data, setData] = useState(DEFAULT);
  const [hasResult, setHasResult] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.activity.trim()) return setError("Please enter today's activity.");
    const labour = parseInt(form.labour_count, 10);
    if (!Number.isFinite(labour) || labour < 0) return setError("Labour count must be a non-negative number.");
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/site-assistant", { ...form, labour_count: labour });
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
    <Page title="Daily Site Assistant" subtitle="Plan today's work, resources and safety checks in seconds.">
      <ModuleLayout
        loading={loading} error={error} hasResult={hasResult}
        emptyIcon={Calendar} emptyText="Enter today's activity, crew size and site conditions to get a daily plan."
        form={
          <form className="form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="s-act">Today's activity *</label>
              <input id="s-act" value={form.activity} onChange={set("activity")} placeholder="e.g. First floor slab casting" />
            </div>
            <div className="field">
              <label htmlFor="s-lab">Labour count *</label>
              <input id="s-lab" type="number" min="0" value={form.labour_count} onChange={set("labour_count")} placeholder="20" />
            </div>
            <div className="field">
              <label htmlFor="s-cond">Site condition</label>
              <textarea id="s-cond" value={form.site_condition} onChange={set("site_condition")}
                placeholder="e.g. Ground muddy after overnight rain, transit mixer access limited" />
            </div>
            <button className="btn" disabled={loading}>
              <ClipboardCheck size={18} /> {loading ? "Planning…" : "Generate Daily Plan"}
            </button>
          </form>
        }
      >
        <div className="result-head"><h3>Today's Plan</h3></div>
        <ListBlock title="Tasks" items={data?.tasks || []} icon={ListChecks} />
        <ListBlock title="Materials & equipment" items={data?.materials_equipment || []} icon={Package} />
        <ListBlock title="Safety checks" items={data?.safety_checks || []} icon={ClipboardCheck} />
        <ListBlock title="Risk alerts" items={data?.risk_alerts || []} icon={AlertTriangle} />
      </ModuleLayout>
    </Page>
  );
}
