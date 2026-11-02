import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, ImagePlus, Loader2, X } from "lucide-react";

const MAX_BYTES = 4 * 1024 * 1024;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

export function Page({ title, subtitle, children }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
      <header className="page-header">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </header>
      {children}
    </motion.div>
  );
}

/** Drag-and-drop image picker with preview, remove button and client-side validation. */
export function ImageDrop({ file, onChange, onError, label = "Upload site photo (optional)" }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [preview, setPreview] = useState(null);

  const accept = (f) => {
    if (!f) return;
    if (!TYPES.includes(f.type)) return onError?.("Only JPG, PNG or WEBP images are allowed.");
    if (f.size > MAX_BYTES) return onError?.("Image is too large. Maximum size is 4 MB.");
    onError?.("");
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(f));
    onChange(f);
  };

  const clear = (e) => {
    e.stopPropagation();
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
    onChange(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div
      className={`dropzone ${drag ? "dragging" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDrag(true);
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDrag(false);
        accept(e.dataTransfer.files?.[0]);
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(e) => accept(e.target.files?.[0])}
      />
      {file && preview ? (
        <div className="preview">
          <img src={preview} alt="Selected upload preview" />
          <button type="button" className="remove-btn" onClick={clear} aria-label="Remove image">
            <X size={16} />
          </button>
          <span className="preview-name">{file.name}</span>
        </div>
      ) : (
        <div className="drop-hint">
          <ImagePlus size={28} />
          <span>{label}</span>
          <small>Drag & drop or click · JPG, PNG, WEBP · max 4 MB</small>
        </div>
      )}
    </div>
  );
}

export function Spinner({ text = "Analyzing with AI…" }) {
  return (
    <div className="spinner-wrap">
      <Loader2 className="spin" size={32} />
      <span>{text}</span>
    </div>
  );
}

export function ErrorMsg({ message }) {
  if (!message) return null;
  return (
    <div className="error-msg" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ icon: Icon, text }) {
  return (
    <div className="empty-state">
      {Icon && <Icon size={48} />}
      <p>{text}</p>
    </div>
  );
}

const BADGE_COLORS = {
  low: "green", minor: "green", proceed: "green", none: "green", hairline: "green",
  medium: "amber", moderate: "amber", "proceed with caution": "amber", vertical: "amber", horizontal: "amber",
  high: "red", critical: "red", severe: "red", postpone: "red", structural: "red", diagonal: "red",
};

export function Badge({ value }) {
  const color = BADGE_COLORS[String(value || "").toLowerCase()] || "grey";
  return <span className={`badge badge-${color}`}>{value || "—"}</span>;
}

export function ListBlock({ title, items, icon: Icon }) {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) return null;
  return (
    <div className="list-block">
      <h4>
        {Icon && <Icon size={16} />} {title}
      </h4>
      <ul>
        {list.map((item, i) => (
          <li key={i}>{typeof item === "string" ? item : JSON.stringify(item)}</li>
        ))}
      </ul>
    </div>
  );
}

/** Standard two-column module layout: form card left, results card right. */
export function ModuleLayout({ form, loading, error, hasResult, emptyIcon, emptyText, children }) {
  return (
    <div className="grid-2">
      <div className="card">{form}</div>
      <div className="card result-card">
        <ErrorMsg message={error} />
        {loading ? (
          <Spinner />
        ) : hasResult ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
            {children}
          </motion.div>
        ) : (
          !error && <EmptyState icon={emptyIcon} text={emptyText} />
        )}
      </div>
    </div>
  );
}
