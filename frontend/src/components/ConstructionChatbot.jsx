import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Loader2, Send, Trash2 } from "lucide-react";
import api, { errorMessage } from "../api.js";
import { Page } from "./common.jsx";

const GREETING = {
  role: "assistant",
  text: "Namaste! I'm your ConstructAI assistant. Ask me about materials, IS codes, costs, site safety or anything construction.",
};
const STARTERS = ["Which cement grade for RCC slabs?", "How long should concrete be cured?", "Cost per sq ft for a house in Pune?"];

export default function ConstructionChatbot() {
  const [messages, setMessages] = useState([GREETING]);
  const [suggestions, setSuggestions] = useState(STARTERS);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text) => {
    const query = (text ?? input).trim();
    if (!query || loading) return;
    const history = messages.filter((m) => m.role !== "error").map(({ role, text }) => ({ role, text }));
    setMessages((m) => [...m, { role: "user", text: query }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.post("/api/chatbot", { query, history });
      const reply = res.data?.reply;
      if (res.data?.error || !reply) {
        setMessages((m) => [...m, { role: "error", text: res.data?.error || "No reply received. Please retry." }]);
      } else {
        setMessages((m) => [...m, { role: "assistant", text: reply }]);
      }
      setSuggestions(res.data?.action_suggestions || []);
    } catch (err) {
      setMessages((m) => [...m, { role: "error", text: errorMessage(err) }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page title="Construction Chatbot" subtitle="Your always-on construction expert, with conversation memory.">
      <div className="card chat-card">
        <div className="chat-messages">
          {messages.map((m, i) => (
            <motion.div key={i} className={`bubble ${m.role}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              {m.text}
            </motion.div>
          ))}
          {loading && (
            <div className="bubble assistant"><Loader2 className="spin" size={16} /> Thinking…</div>
          )}
          <div ref={endRef} />
        </div>
        {(suggestions || []).length > 0 && !loading && (
          <div className="chips">
            {(suggestions || []).map((s, i) => (
              <button key={i} className="chip" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}
        <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <button type="button" className="btn btn-ghost" title="Clear chat" aria-label="Clear chat"
            onClick={() => { setMessages([GREETING]); setSuggestions(STARTERS); }}>
            <Trash2 size={16} />
          </button>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your question…" aria-label="Message" />
          <button className="btn" disabled={loading || !input.trim()} aria-label="Send"><Send size={16} /></button>
        </form>
      </div>
    </Page>
  );
}
