import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Target, DollarSign, Users, AlertCircle, Lightbulb } from 'lucide-react';

const PLATFORMS = [
  { id: 'google', name: 'Google Ads', color: '#4285F4', icon: '🔍' },
  { id: 'meta', name: 'Meta Ads', color: '#1877F2', icon: '👥' },
  { id: 'tiktok', name: 'TikTok Ads', color: '#000000', icon: '🎵' }
];

export default function PlatformComparison({ apiBase }) {
  const [totalBudget, setTotalBudget] = useState(1000);
  const [allocations, setAllocations] = useState({
    google: 40,
    meta: 40,
    tiktok: 20
  });
  const [goal, setGoal] = useState('purchases');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [draggedPlatform, setDraggedPlatform] = useState(null);

  const handleSliderChange = (platform, value) => {
    const newValue = parseFloat(value);
    const others = PLATFORMS.filter(p => p.id !== platform).map(p => p.id);
    const otherTotal = others.reduce((sum, p) => sum + allocations[p], 0);
    
    if (newValue + otherTotal > 100) {
      const excess = (newValue + otherTotal) - 100;
      const ratio = otherTotal > 0 ? (otherTotal - excess) / otherTotal : 0;
      
      setAllocations({
        ...allocations,
        [platform]: newValue,
        [others[0]]: allocations[others[0]] * ratio,
        [others[1]]: allocations[others[1]] * ratio
      });
    } else {
      setAllocations({
        ...allocations,
        [platform]: newValue
      });
    }
  };

  const normalize = () => {
    const total = Object.values(allocations).reduce((sum, v) => sum + v, 0);
    if (Math.abs(total - 100) > 0.01) {
      const factor = 100 / total;
      setAllocations({
        google: allocations.google * factor,
        meta: allocations.meta * factor,
        tiktok: allocations.tiktok * factor
      });
    }
  };

  const runComparison = async () => {
    normalize();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBase}/aria/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          total_budget: totalBudget,
          goal: goal,
          allocations: PLATFORMS.map(p => ({
            platform: p.id,
            percentage: allocations[p.id]
          }))
        })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Comparison failed');
      }

      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const total = Object.values(allocations).reduce((sum, v) => sum + v, 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Platform Comparison Lab
          </h1>
          <p className="text-slate-400">AI-powered competitive analysis across Google, Meta, and TikTok</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Budget Configuration */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-green-400" />
              Campaign Budget
            </h2>
            
            <div className="mb-6">
              <label className="block text-sm text-slate-400 mb-2">Total Daily Budget ($)</label>
              <input
                type="number"
                value={totalBudget}
                onChange={(e) => setTotalBudget(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                min="0"
                step="100"
              />
            </div>

            <div className="mb-6">
              <label className="block text-sm text-slate-400 mb-2">Campaign Goal</label>
              <select
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
              >
                <option value="purchases">Purchases</option>
                <option value="leads">Leads</option>
                <option value="awareness">Awareness</option>
                <option value="installs">App Installs</option>
              </select>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 mb-4">
              <div className="text-sm text-slate-400 mb-2">Allocation Total</div>
              <div className={`text-2xl font-bold ${Math.abs(total - 100) < 0.1 ? 'text-green-400' : 'text-yellow-400'}`}>
                {total.toFixed(1)}%
              </div>
            </div>

            <button
              onClick={runComparison}
              disabled={loading || Math.abs(total - 100) > 0.1}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:from-slate-600 disabled:to-slate-700 disabled:cursor-not-allowed rounded-lg px-6 py-3 font-semibold transition-all"
            >
              {loading ? 'Analyzing...' : 'Run AI Comparison'}
            </button>

            {error && (
              <div className="mt-4 bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm">
                {error}
              </div>
            )}
          </div>

          {/* Interactive Allocation */}
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-purple-400" />
              Budget Allocation
            </h2>

            <div className="space-y-6">
              {PLATFORMS.map(platform => (
                <div key={platform.id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{platform.icon}</span>
                      <span className="font-medium">{platform.name}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold" style={{ color: platform.color }}>
                        {allocations[platform.id].toFixed(1)}%
                      </div>
                      <div className="text-xs text-slate-400">
                        ${(totalBudget * allocations[platform.id] / 100).toFixed(0)}/day
                      </div>
                    </div>
                  </div>
                  
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="0.1"
                    value={allocations[platform.id]}
                    onChange={(e) => handleSliderChange(platform.id, e.target.value)}
                    className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                    style={{
                      background: `linear-gradient(to right, ${platform.color} 0%, ${platform.color} ${allocations[platform.id]}%, #334155 ${allocations[platform.id]}%, #334155 100%)`
                    }}
                  />
                </div>
              ))}
            </div>

            <button
              onClick={normalize}
              className="mt-6 w-full bg-slate-700 hover:bg-slate-600 rounded-lg px-4 py-2 text-sm transition-all"
            >
              Normalize to 100%
            </button>
          </div>
        </div>

        {/* Analysis Results */}
        {analysis && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Platform Metrics Comparison */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-400" />
                Platform Performance Analysis
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {analysis.platform_metrics.map(metric => {
                  const platform = PLATFORMS.find(p => p.id === metric.platform);
                  return (
                    <div key={metric.platform} className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                      <div className="flex items-center gap-2 mb-4">
                        <span className="text-2xl">{platform.icon}</span>
                        <h3 className="font-semibold" style={{ color: platform.color }}>{platform.name}</h3>
                      </div>

                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Est. Reach</span>
                          <span className="font-semibold">{metric.estimated_reach.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Est. CPA</span>
                          <span className="font-semibold">${metric.estimated_cpa.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Est. CTR</span>
                          <span className="font-semibold">{(metric.estimated_ctr * 100).toFixed(2)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Est. CVR</span>
                          <span className="font-semibold">{(metric.estimated_cvr * 100).toFixed(2)}%</span>
                        </div>

                        <div className="pt-2 border-t border-slate-700">
                          <div className="mb-2">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-400">Audience Fit</span>
                              <span>{(metric.audience_fit_score * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full bg-slate-700 rounded-full h-2">
                              <div
                                className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full"
                                style={{ width: `${metric.audience_fit_score * 100}%` }}
                              />
                            </div>
                          </div>

                          <div className="mb-2">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-400">Creative Fit</span>
                              <span>{(metric.creative_format_score * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full bg-slate-700 rounded-full h-2">
                              <div
                                className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full"
                                style={{ width: `${metric.creative_format_score * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>

                        <div className="pt-2 border-t border-slate-700">
                          <div className="text-xs text-slate-400 mb-1">Competition</div>
                          <div className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                            metric.competitive_intensity === 'low' ? 'bg-green-500/20 text-green-400' :
                            metric.competitive_intensity === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-red-500/20 text-red-400'
                          }`}>
                            {metric.competitive_intensity.toUpperCase()}
                          </div>
                        </div>

                        <div className="pt-2 border-t border-slate-700">
                          <div className="text-xs text-slate-400 mb-1">Recommendation</div>
                          <div className="text-xs text-slate-300">{metric.recommendation}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Overall Insights */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Users className="w-5 h-5 text-blue-400" />
                  Overall Recommendation
                </h3>
                <p className="text-slate-300 text-sm leading-relaxed">{analysis.overall_recommendation}</p>
              </div>

              <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-yellow-400" />
                  Risk Assessment
                </h3>
                <p className="text-slate-300 text-sm leading-relaxed">{analysis.risk_assessment}</p>
              </div>
            </div>

            {/* Optimization Tips */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-yellow-400" />
                Optimization Tips
              </h3>
              <ul className="space-y-2">
                {analysis.optimization_tips.map((tip, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="text-purple-400 mt-1">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
