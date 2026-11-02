import { useState } from "react";
import { BrowserRouter, Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity, ArrowRight, BookOpen, Building2, Calendar, ClipboardList, CloudRain,
  HardHat, LayoutDashboard, Menu, MessageSquare, ShieldAlert, X,
} from "lucide-react";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import SafetyMonitor from "./components/SafetyMonitor.jsx";
import CrackDetection from "./components/CrackDetection.jsx";
import Valuation from "./components/Valuation.jsx";
import ProjectPlanner from "./components/ProjectPlanner.jsx";
import KnowledgeBase from "./components/KnowledgeBase.jsx";
import ConstructionChatbot from "./components/ConstructionChatbot.jsx";
import DailySiteAssistant from "./components/DailySiteAssistant.jsx";
import WeatherAdvisor from "./components/WeatherAdvisor.jsx";

const FEATURES = [
  { path: "/safety", label: "Safety Monitor", icon: ShieldAlert, element: SafetyMonitor,
    desc: "Detect hazards and missing PPE from site photos with OSHA & IS references." },
  { path: "/cracks", label: "Crack Detection", icon: Activity, element: CrackDetection,
    desc: "Classify cracks, assess severity and get repair & prevention methods." },
  { path: "/valuation", label: "Valuation", icon: Building2, element: Valuation,
    desc: "Estimate property value, rental income and ROI in ₹ for Indian markets." },
  { path: "/planner", label: "Project Planner", icon: ClipboardList, element: ProjectPlanner,
    desc: "Material quantities, cost breakdown, timeline and a concept rendering." },
  { path: "/knowledge", label: "Knowledge Base", icon: BookOpen, element: KnowledgeBase,
    desc: "Explain concepts, look up IS codes and generate site documents." },
  { path: "/chat", label: "AI Chatbot", icon: MessageSquare, element: ConstructionChatbot,
    desc: "Ask anything about construction — with conversation memory." },
  { path: "/site-assistant", label: "Site Assistant", icon: Calendar, element: DailySiteAssistant,
    desc: "Daily task plan, materials, safety checks and risk alerts." },
  { path: "/weather", label: "Weather Advisor", icon: CloudRain, element: WeatherAdvisor,
    desc: "Proceed / caution / postpone decisions using live weather data." },
];

function Dashboard() {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
      <header className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">
          Multimodal construction intelligence — eight AI tools for safer, faster and smarter sites.
        </p>
      </header>
      <div className="feature-grid">
        {FEATURES.map(({ path, label, icon: Icon, desc }, i) => (
          <motion.div key={path} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.3 }}>
            <Link to={path} className="card feature-card">
              <div className="feature-icon"><Icon size={26} /></div>
              <h3>{label}</h3>
              <p>{desc}</p>
              <span className="feature-link">Open <ArrowRight size={14} /></span>
            </Link>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

function NotFound() {
  return (
    <div className="card empty-state">
      <h3>Page not found</h3>
      <Link to="/" className="btn">Back to dashboard</Link>
    </div>
  );
}

function Shell() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="layout">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-top">
          <Link to="/" className="brand" onClick={() => setOpen(false)}>
            <HardHat size={28} className="text-orange" />
            <span>Construct<span className="text-orange">AI</span></span>
          </Link>
          <button className="menu-toggle" onClick={() => setOpen((o) => !o)} aria-label="Toggle navigation">
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
        <nav className="nav" onClick={() => setOpen(false)}>
          <NavLink to="/" end className="nav-link"><LayoutDashboard size={18} /> Dashboard</NavLink>
          {FEATURES.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} className="nav-link"><Icon size={18} /> {label}</NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">
        <div className="content">
          <ErrorBoundary key={location.pathname}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              {FEATURES.map(({ path, element: Element }) => (
                <Route key={path} path={path} element={<Element />} />
              ))}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </ErrorBoundary>
        </div>
        <footer className="footer">
          AI-generated insights are indicative and not a substitute for professional engineering advice.
        </footer>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
