import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";

import App from "./App";
import PlatformComparison3D from "./components/PlatformComparison3D";
import MemoryView from "./components/MemoryView";
import AgentLogs from "./components/AgentLogs";
import { apiBase } from "./api";
import "./styles.css";

function Navigation() {
  const location = useLocation();
  
  const isActive = (path) => location.pathname === path;
  
  return (
    <nav className="route-nav">
      <div className="route-nav-inner">
        <Link 
          to="/" 
          className={`route-link ${
            isActive('/') ? 'active' : ''
          }`}
        >
          📊 Dashboard
        </Link>
        <Link 
          to="/compare" 
          className={`route-link ${
            isActive('/compare') ? 'active' : ''
          }`}
        >
          🎨 Platform Comparison
        </Link>
        <Link 
          to="/memory" 
          className={`route-link ${
            isActive('/memory') ? 'active' : ''
          }`}
        >
          🧠 Shared Memory
        </Link>
        <Link 
          to="/logs" 
          className={`route-link ${
            isActive('/logs') ? 'active' : ''
          }`}
        >
          📝 Agent Logs
        </Link>
      </div>
    </nav>
  );
}

function Root() {
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/compare" element={<PlatformComparison3D apiBase={apiBase} />} />
        <Route path="/memory" element={<MemoryView apiBase={apiBase} />} />
        <Route path="/logs" element={<AppWithLogs />} />
      </Routes>
    </BrowserRouter>
  );
}

// Wrapper to pass App's state to AgentLogs
function AppWithLogs() {
  const [events, setEvents] = React.useState([]);
  const [status, setStatus] = React.useState(null);
  
  React.useEffect(() => {
    let statusInterval = null;

    const refreshStatus = () => {
      fetch(`${apiBase}/aria/status`)
        .then((r) => r.json())
        .then(setStatus)
        .catch(() => {});
    };

    // Connect to WebSocket for real-time events
    const wsBase = apiBase.replace("https", "wss").replace("http", "ws");
    const ws = new WebSocket(`${wsBase}/aria/live`);
    
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setEvents((prev) => [parsed, ...prev].slice(0, 200));

        // keep logs page agent states in sync as events stream
        if (parsed?.agent) {
          setStatus((prev) => {
            if (!prev) return prev;
            const nextAgentStates = { ...(prev.agent_states || {}) };
            Object.keys(nextAgentStates).forEach((name) => {
              if (name !== parsed.agent) {
                nextAgentStates[name] = {
                  ...(nextAgentStates[name] || {}),
                  status: "idle",
                };
              }
            });
            nextAgentStates[parsed.agent] = {
              ...(nextAgentStates[parsed.agent] || {}),
              status: "running",
              updated_at: parsed.timestamp,
            };
            return {
              ...prev,
              agent_states: nextAgentStates,
              iteration: parsed.iteration ?? prev.iteration,
            };
          });
        }
      } catch {}
    };
    
    refreshStatus();
    statusInterval = setInterval(refreshStatus, 2500);
    
    return () => {
      ws.close();
      if (statusInterval) clearInterval(statusInterval);
    };
  }, []);
  
  return <AgentLogs events={events} status={status} />;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
