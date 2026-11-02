import axios from "axios";

// Relative "/api" in production (same Vercel project); Vite proxies it to FastAPI in dev.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 90000,
});

/** Turn any axios failure into a readable message (prefers the backend's `detail`). */
export function errorMessage(err) {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  if (err?.code === "ECONNABORTED") return "The request timed out. Please retry.";
  if (!err?.response) return "Cannot reach the server. Check your connection and retry.";
  return `Request failed (HTTP ${err.response.status}). Please retry.`;
}

export const formatINR = (n) => {
  const num = Number(n);
  if (!Number.isFinite(num)) return "₹0";
  return "₹" + Math.round(num).toLocaleString("en-IN");
};

export default api;
