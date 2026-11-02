import { useState } from "react";
import { BookMarked, BookOpen, Copy, Lightbulb, Send } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { ListBlock, ModuleLayout, Page } from "./common.jsx";

const DEFAULT = { title: "", content: "", key_points: [], references: [] };

const TABS = [
  { mode: "explain", label: "Explain Concept", placeholder: "e.g. What is the difference between one-way and two-way slabs?" },
  { mode: "standards", label: "IS Codes & Standards", placeholder: "e.g. IS 456 requirements for minimum cover in columns" },
  { mode: "document", label: "Generate Document", placeholder: "e.g. Method statement for excavation up to 3 m depth" },
];

export default function KnowledgeBase() {
  const [mode, setMode] = useState("explain");
  const [query, setQuery] = useState("");
  const [data, setData] = useState(DEFAULT);
  const [hasResult, setHasResult] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const tab = TABS.find((t) => t.mode === mode) || TABS[0];

  const submit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return setError("Please enter a question or topic.");
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/knowledge-base", { query, mode });
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
    <Page title="Knowledge Base" subtitle="Construction concepts, Indian standards and ready-to-use site documents.">
      <ModuleLayout
        loading={loading} error={error} hasResult={hasResult}
        emptyIcon={BookOpen} emptyText="Pick a tab, ask a question and the answer will appear here."
        form={
          <form className="form" onSubmit={submit}>
            <div className="tabs" role="tablist">
              {TABS.map((t) => (
                <button key={t.mode} type="button" role="tab" aria-selected={mode === t.mode}
                  className={`tab ${mode === t.mode ? "active" : ""}`} onClick={() => setMode(t.mode)}>
                  {t.label}
                </button>
              ))}
            </div>
            <div className="field">
              <label htmlFor="kb-q">{tab.label}</label>
              <textarea id="kb-q" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={tab.placeholder} />
            </div>
            <button className="btn" disabled={loading}>
              <Send size={18} /> {loading ? "Thinking…" : "Ask"}
            </button>
          </form>
        }
      >
        <div className="result-head">
          <h3>{data?.title || "Answer"}</h3>
          {data?.content && (
            <button type="button" className="btn btn-ghost" onClick={() => navigator.clipboard?.writeText(data.content)}>
              <Copy size={14} /> Copy
            </button>
          )}
        </div>
        {data?.content && <p className="doc-content">{data.content}</p>}
        <ListBlock title="Key points" items={data?.key_points || []} icon={Lightbulb} />
        <ListBlock title="References" items={data?.references || []} icon={BookMarked} />
      </ModuleLayout>
    </Page>
  );
}
