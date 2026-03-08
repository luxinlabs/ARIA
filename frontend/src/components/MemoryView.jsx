import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Database, RefreshCw } from "lucide-react";

const SAMPLE_MEMORY = {
  brand_dna: {
    name: "Sample Brand",
    business_type: "B2C",
    voice: "Professional yet approachable",
    usp: "AI-powered solutions that deliver results",
    values: ["Innovation", "Quality", "Customer First"],
  },
  production_information: {
    product_name: "",
    product_category: "",
    offer_summary: "Production information is retrieved from the real website during initialization.",
    price_point: "",
    brand_url: "",
  },
  target_audience: {
    primary_segment: "Small to Medium Businesses",
    age_range: "25-45",
    geography: ["United States", "Canada", "United Kingdom"],
    interests: ["Digital Marketing", "Technology", "Business Growth"],
    belief_state: "Seeking efficient marketing solutions",
    key_objections: ["Budget constraints", "Learning curve"],
  },
  platform_context: {
    channels: ["webads", "images", "videos"],
    images_required: 5,
    videos_required: 2,
  },
  strategy_memory: {
    iteration: 0,
    current_winning_angle: "Not yet determined",
    performance_trajectory: [],
    human_decisions: [],
  },
  experiment_log: [],
};

export default function MemoryView({ apiBase }) {
  const [memory, setMemory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isSample, setIsSample] = useState(false);
  const [expanded, setExpanded] = useState({
    brand: true,
    production: true,
    audience: true,
    platform: false,
    strategy: true,
    human: true,
    experiments: false,
  });

  const fetchMemory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/aria/memory`);
      if (!res.ok) throw new Error("memory fetch failed");
      const data = await res.json();
      const hasRealMemory = Boolean(data?.brand_dna?.name);
      setMemory(hasRealMemory ? data : SAMPLE_MEMORY);
      setIsSample(!hasRealMemory);
    } catch {
      setMemory(SAMPLE_MEMORY);
      setIsSample(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
    const id = setInterval(fetchMemory, 5000);
    return () => clearInterval(id);
  }, [apiBase]);

  const humanDecisions = useMemo(
    () => memory?.strategy_memory?.human_decisions || [],
    [memory],
  );

  if (!memory) {
    return (
      <div className="app-shell">
        <section className="glass panel span-2 memory-empty">
          <h2>Loading Shared Memory...</h2>
        </section>
      </div>
    );
  }

  return (
    <div className="app-shell memory-shell">
      <section className="glass topbar memory-topbar">
        <div>
          <p className="eyebrow">Knowledge Base</p>
          <h1>Shared Memory</h1>
        </div>
        <button className="primary" onClick={fetchMemory} disabled={loading}>
          <RefreshCw size={15} /> {loading ? "Refreshing" : "Refresh"}
        </button>
      </section>

      {isSample ? (
        <section className="glass memory-banner">
          <b>Sample view shown.</b> Initialize ARIA with a valid website URL to retrieve real production information.
        </section>
      ) : null}

      <main className="memory-grid">
        <MemorySection
          title="Brand DNA"
          expanded={expanded.brand}
          onToggle={() => setExpanded((p) => ({ ...p, brand: !p.brand }))}
        >
          <InfoGrid
            items={[
              ["Name", memory.brand_dna?.name],
              ["Business Type", memory.brand_dna?.business_type],
              ["Voice", memory.brand_dna?.voice],
              ["USP", memory.brand_dna?.usp],
            ]}
          />
        </MemorySection>

        <MemorySection
          title="Production Information"
          expanded={expanded.production}
          onToggle={() => setExpanded((p) => ({ ...p, production: !p.production }))}
        >
          <InfoGrid
            items={[
              ["Product", memory.production_information?.product_name],
              ["Category", memory.production_information?.product_category],
              ["Price", memory.production_information?.price_point],
              ["Brand URL", memory.production_information?.brand_url],
            ]}
          />
          <p className="memory-note">{memory.production_information?.offer_summary}</p>
        </MemorySection>

        <MemorySection
          title="Target Audience"
          expanded={expanded.audience}
          onToggle={() => setExpanded((p) => ({ ...p, audience: !p.audience }))}
        >
          <InfoGrid
            items={[
              ["Primary Segment", memory.target_audience?.primary_segment],
              ["Age Range", memory.target_audience?.age_range],
              ["Belief State", memory.target_audience?.belief_state],
            ]}
          />
          <TagRow title="Geography" values={memory.target_audience?.geography || []} />
          <TagRow title="Interests" values={memory.target_audience?.interests || []} />
          <TagRow title="Objections" values={memory.target_audience?.key_objections || []} />
        </MemorySection>

        <MemorySection
          title="Platform Context"
          expanded={expanded.platform}
          onToggle={() => setExpanded((p) => ({ ...p, platform: !p.platform }))}
        >
          <InfoGrid
            items={[
              ["Images Required", memory.platform_context?.images_required],
              ["Videos Required", memory.platform_context?.videos_required],
            ]}
          />
          <TagRow title="Channels" values={memory.platform_context?.channels || []} />
        </MemorySection>

        <MemorySection
          title="Strategy Memory"
          expanded={expanded.strategy}
          onToggle={() => setExpanded((p) => ({ ...p, strategy: !p.strategy }))}
        >
          <InfoGrid
            items={[
              ["Iteration", memory.strategy_memory?.iteration],
              ["Winning Angle", memory.strategy_memory?.current_winning_angle],
            ]}
          />
        </MemorySection>

        <MemorySection
          title={`Human Input Decisions (${humanDecisions.length})`}
          expanded={expanded.human}
          onToggle={() => setExpanded((p) => ({ ...p, human: !p.human }))}
        >
          {humanDecisions.length === 0 ? (
            <p className="memory-note">No human decisions saved yet.</p>
          ) : (
            <div className="memory-list">
              {humanDecisions.slice(-6).reverse().map((d, idx) => (
                <article key={idx} className="memory-list-item">
                  <div className="memory-list-head">
                    <b>{d.decision_type}</b>
                    <small>{new Date(d.timestamp).toLocaleString()}</small>
                  </div>
                  <p>{d.rationale}</p>
                </article>
              ))}
            </div>
          )}
        </MemorySection>

        <MemorySection
          title={`Experiment Log (${memory.experiment_log?.length || 0})`}
          expanded={expanded.experiments}
          onToggle={() => setExpanded((p) => ({ ...p, experiments: !p.experiments }))}
        >
          {!memory.experiment_log?.length ? (
            <p className="memory-note">No experiments recorded yet.</p>
          ) : (
            <div className="memory-list">
              {memory.experiment_log.slice(-6).reverse().map((exp, idx) => (
                <article key={idx} className="memory-list-item">
                  <div className="memory-list-head">
                    <b>{exp.hypothesis}</b>
                    <small>{exp.result}</small>
                  </div>
                  <p>{exp.learning}</p>
                </article>
              ))}
            </div>
          )}
        </MemorySection>
      </main>
    </div>
  );
}

function MemorySection({ title, expanded, onToggle, children }) {
  return (
    <section className="glass memory-section">
      <button className="memory-section-head" onClick={onToggle}>
        <h2>{title}</h2>
        {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
      </button>
      {expanded ? <div className="memory-section-body">{children}</div> : null}
    </section>
  );
}

function InfoGrid({ items }) {
  return (
    <div className="memory-info-grid">
      {items.map(([label, value]) => (
        <div className="memory-info-item" key={label}>
          <small>{label}</small>
          <b>{value || "N/A"}</b>
        </div>
      ))}
    </div>
  );
}

function TagRow({ title, values }) {
  if (!values.length) return null;
  return (
    <div className="memory-tags-wrap">
      <small>{title}</small>
      <div className="memory-tags">
        {values.map((v, idx) => (
          <span key={`${title}-${idx}`}>{v}</span>
        ))}
      </div>
    </div>
  );
}
