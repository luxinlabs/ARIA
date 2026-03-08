import { useMemo, useState } from "react";
import { Activity, Clock, Zap } from "lucide-react";

const AGENT_INFO = {
  observe: { name: "Signal Observer", color: "#3b82f6", emoji: "🔍", description: "Analyzes market signals and competitor activity" },
  strategist: { name: "Growth Strategist", color: "#8b5cf6", emoji: "🎯", description: "Generates data-driven hypotheses" },
  creative: { name: "Creative Generator", color: "#ec4899", emoji: "✨", description: "Creates ad variants and copy" },
  audience: { name: "Audience Optimizer", color: "#10b981", emoji: "👥", description: "Refines targeting parameters" },
  budget: { name: "Budget Allocator", color: "#f59e0b", emoji: "💰", description: "Distributes budget across platforms" },
  execute: { name: "Execution Layer", color: "#06b6d4", emoji: "🚀", description: "Launches campaigns on platforms" },
  evaluate: { name: "Experiment Evaluator", color: "#14b8a6", emoji: "📊", description: "Analyzes experiment results" },
  learn: { name: "Learning Agent", color: "#6366f1", emoji: "🧠", description: "Persists learnings to memory" },
  notify: { name: "Notification Agent", color: "#84cc16", emoji: "📢", description: "Sends alerts to stakeholders" },
};

export default function AgentLogs({ events, status }) {
  const [filter, setFilter] = useState("all");

  const filteredEvents = useMemo(
    () => (filter === "all" ? events : events.filter((e) => e.agent === filter)),
    [events, filter],
  );

  const currentAgent = useMemo(
    () =>
      Object.entries(status?.agent_states || {}).find(
        ([, state]) => state?.status === "running" || state?.status === "thinking",
      )?.[0],
    [status],
  );

  const active = currentAgent ? AGENT_INFO[currentAgent] : null;

  return (
    <div className="app-shell logs-shell">
      <section className="glass topbar logs-topbar">
        <div>
          <p className="eyebrow">Observability</p>
          <h1>Agent Logs</h1>
        </div>
        <div className="status-pill">{events.length} Events</div>
      </section>

      {active ? (
        <section className="glass logs-active">
          <div className="logs-active-badge">{active.emoji}</div>
          <div>
            <small>Currently Active</small>
            <h2>{active.name}</h2>
            <p>{active.description}</p>
          </div>
          <div className="logs-running">
            <Zap size={14} /> RUNNING
          </div>
        </section>
      ) : (
        <section className="glass logs-active">
          <div className="logs-active-badge">⏸️</div>
          <div>
            <small>Currently Active</small>
            <h2>No Active Agent</h2>
            <p>Run one cycle to see live execution.</p>
          </div>
        </section>
      )}

      <section className="glass logs-filter">
        <h2>
          <Activity size={16} /> Agents
        </h2>
        <div className="logs-filter-grid">
          {Object.entries(AGENT_INFO).map(([key, info]) => {
            const st = status?.agent_states?.[key]?.status || "idle";
            return (
              <button
                key={key}
                className={`logs-agent-chip ${filter === key ? "active" : ""}`}
                onClick={() => setFilter((prev) => (prev === key ? "all" : key))}
              >
                <span>{info.emoji}</span>
                <b>{info.name}</b>
                <small>{st}</small>
              </button>
            );
          })}
        </div>
      </section>

      <section className="glass logs-timeline">
        <header>
          <h2>
            <Clock size={16} /> Timeline ({filteredEvents.length})
          </h2>
          <button onClick={() => setFilter("all")}>Clear Filter</button>
        </header>

        <div className="logs-list">
          {filteredEvents.length === 0 ? (
            <p className="memory-note">No events yet. Initialize ARIA and run a cycle.</p>
          ) : (
            filteredEvents.map((event, idx) => {
              const info = AGENT_INFO[event.agent] || { name: event.agent || "Unknown", emoji: "•", color: "#9ca3af" };
              return (
                <article className="logs-list-item" key={event.event_id || idx}>
                  <div className="logs-item-head">
                    <span className="logs-emoji">{info.emoji}</span>
                    <b style={{ color: info.color }}>{info.name}</b>
                    <small>{event.action}</small>
                  </div>
                  <p>{event.reason}</p>
                  <time>{event.timestamp ? new Date(event.timestamp).toLocaleString() : ""}</time>
                </article>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
