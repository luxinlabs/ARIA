import { useState, useEffect, useRef, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Html, PerspectiveCamera, Environment } from '@react-three/drei';
import { motion } from 'framer-motion';
import * as THREE from 'three';
import { TrendingUp, Target, DollarSign, Lightbulb, AlertCircle, Maximize2 } from 'lucide-react';

const PLATFORMS = [
  { id: 'google', name: 'Google Ads', color: '#4285F4', emoji: '🔍' },
  { id: 'meta', name: 'Meta Ads', color: '#1877F2', emoji: '👥' },
  { id: 'tiktok', name: 'TikTok Ads', color: '#000000', emoji: '🎵' }
];

// Draggable 3D Platform Node
function PlatformNode({ platform, position, onDrag, isActive, budget, allocations }) {
  const meshRef = useRef();
  const [isDragging, setIsDragging] = useState(false);
  const [hovered, setHovered] = useState(false);
  const { camera, gl, size } = useThree();

  useFrame((state) => {
    if (meshRef.current && !isDragging) {
      meshRef.current.rotation.y += 0.005;
      const scale = hovered ? 1.2 : 1;
      meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.1);
    }
  });

  const handlePointerDown = (e) => {
    e.stopPropagation();
    setIsDragging(true);
    gl.domElement.style.cursor = 'grabbing';
  };

  const handlePointerMove = (e) => {
    if (!isDragging) return;
    e.stopPropagation();

    const vec = new THREE.Vector3();
    const pos = new THREE.Vector3();
    
    vec.set(
      (e.clientX / size.width) * 2 - 1,
      -(e.clientY / size.height) * 2 + 1,
      0.5
    );
    
    vec.unproject(camera);
    vec.sub(camera.position).normalize();
    const distance = -camera.position.z / vec.z;
    pos.copy(camera.position).add(vec.multiplyScalar(distance));

    // Constrain to triangle bounds
    const constrainedPos = constrainToTriangle(pos.x, pos.y);
    onDrag(platform.id, constrainedPos);
  };

  const handlePointerUp = () => {
    setIsDragging(false);
    gl.domElement.style.cursor = hovered ? 'grab' : 'auto';
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('pointermove', handlePointerMove);
      window.addEventListener('pointerup', handlePointerUp);
      return () => {
        window.removeEventListener('pointermove', handlePointerMove);
        window.removeEventListener('pointerup', handlePointerUp);
      };
    }
  }, [isDragging]);

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onPointerDown={handlePointerDown}
        onPointerEnter={() => {
          setHovered(true);
          gl.domElement.style.cursor = 'grab';
        }}
        onPointerLeave={() => {
          setHovered(false);
          gl.domElement.style.cursor = 'auto';
        }}
      >
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial
          color={platform.color}
          emissive={platform.color}
          emissiveIntensity={isActive ? 0.5 : 0.2}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>
      
      {/* Glow effect */}
      <mesh scale={1.3}>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshBasicMaterial
          color={platform.color}
          transparent
          opacity={hovered ? 0.3 : 0.1}
        />
      </mesh>

      {/* Allocation label showing all three platforms */}
      <Html distanceFactor={10} position={[0, 0.8, 0]}>
        <div className="platform-label" style={{
          background: 'rgba(0,0,0,0.9)',
          padding: '10px 14px',
          borderRadius: '8px',
          border: '2px solid #8b5cf6',
          color: 'white',
          fontSize: '13px',
          fontWeight: 'bold',
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          textAlign: 'left',
          minWidth: '140px'
        }}>
          <div style={{ marginBottom: '4px', fontSize: '11px', color: '#a78bfa' }}>Budget Allocation</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
            <span>🔍</span>
            <span style={{ fontSize: '12px' }}>Google: {allocations.google.toFixed(1)}%</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
            <span>👥</span>
            <span style={{ fontSize: '12px' }}>Meta: {allocations.meta.toFixed(1)}%</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>🎵</span>
            <span style={{ fontSize: '12px' }}>TikTok: {allocations.tiktok.toFixed(1)}%</span>
          </div>
        </div>
      </Html>
    </group>
  );
}

// Triangle boundary for ternary plot
function TriangleBoundary() {
  const points = [
    new THREE.Vector3(0, 4, 0),      // Top (Google)
    new THREE.Vector3(-3.5, -2, 0),  // Bottom Left (Meta)
    new THREE.Vector3(3.5, -2, 0)    // Bottom Right (TikTok)
  ];

  const geometry = new THREE.BufferGeometry().setFromPoints([...points, points[0]]);
  
  return (
    <>
      <line geometry={geometry}>
        <lineBasicMaterial color="#ffffff" linewidth={2} transparent opacity={0.3} />
      </line>
      
      {/* Grid lines */}
      {[0.25, 0.5, 0.75].map((t, i) => (
        <group key={i}>
          <line>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                count={2}
                array={new Float32Array([
                  ...points[0].clone().lerp(points[1], t).toArray(),
                  ...points[2].clone().lerp(points[1], 1 - t).toArray()
                ])}
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial color="#ffffff" transparent opacity={0.1} />
          </line>
        </group>
      ))}

      {/* Axis labels */}
      <Text position={[0, 4.5, 0]} fontSize={0.4} color="#4285F4" anchorX="center">
        Google 100%
      </Text>
      <Text position={[-3.5, -2.5, 0]} fontSize={0.4} color="#1877F2" anchorX="center">
        Meta 100%
      </Text>
      <Text position={[3.5, -2.5, 0]} fontSize={0.4} color="#ffffff" anchorX="center">
        TikTok 100%
      </Text>
    </>
  );
}

// Convert barycentric coordinates to cartesian
function barycentricToCartesian(google, meta, tiktok) {
  const top = new THREE.Vector3(0, 4, 0);
  const left = new THREE.Vector3(-3.5, -2, 0);
  const right = new THREE.Vector3(3.5, -2, 0);
  
  return new THREE.Vector3()
    .addScaledVector(top, google / 100)
    .addScaledVector(left, meta / 100)
    .addScaledVector(right, tiktok / 100);
}

// Convert cartesian to barycentric (approximate)
function cartesianToBarycentric(x, y) {
  const top = { x: 0, y: 4 };
  const left = { x: -3.5, y: -2 };
  const right = { x: 3.5, y: -2 };
  
  const v0 = { x: left.x - top.x, y: left.y - top.y };
  const v1 = { x: right.x - top.x, y: right.y - top.y };
  const v2 = { x: x - top.x, y: y - top.y };
  
  const dot00 = v0.x * v0.x + v0.y * v0.y;
  const dot01 = v0.x * v1.x + v0.y * v1.y;
  const dot02 = v0.x * v2.x + v0.y * v2.y;
  const dot11 = v1.x * v1.x + v1.y * v1.y;
  const dot12 = v1.x * v2.x + v1.y * v2.y;
  
  const invDenom = 1 / (dot00 * dot11 - dot01 * dot01);
  const u = (dot11 * dot02 - dot01 * dot12) * invDenom;
  const v = (dot00 * dot12 - dot01 * dot02) * invDenom;
  
  const meta = Math.max(0, Math.min(100, u * 100));
  const tiktok = Math.max(0, Math.min(100, v * 100));
  const google = Math.max(0, 100 - meta - tiktok);
  
  return { google, meta, tiktok };
}

function constrainToTriangle(x, y) {
  const coords = cartesianToBarycentric(x, y);
  const total = coords.google + coords.meta + coords.tiktok;
  
  if (total > 0) {
    coords.google = (coords.google / total) * 100;
    coords.meta = (coords.meta / total) * 100;
    coords.tiktok = (coords.tiktok / total) * 100;
  }
  
  const pos = barycentricToCartesian(coords.google, coords.meta, coords.tiktok);
  return [pos.x, pos.y, 0];
}

// 3D Scene
function Scene({ allocations, onAllocationChange, totalBudget }) {
  const handleDrag = (platformId, newPosition) => {
    const coords = cartesianToBarycentric(newPosition[0], newPosition[1]);
    onAllocationChange({
      google: coords.google,
      meta: coords.meta,
      tiktok: coords.tiktok
    });
  };

  // Single shared position for all platforms (they move together in ternary plot)
  const sharedPosition = barycentricToCartesian(allocations.google, allocations.meta, allocations.tiktok).toArray();

  return (
    <>
      <PerspectiveCamera makeDefault position={[0, 0, 12]} />
      <OrbitControls enablePan={false} minDistance={8} maxDistance={20} />
      
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, 10]} intensity={0.5} color="#4285F4" />
      
      <TriangleBoundary />
      
      {/* Single draggable node representing the allocation point */}
      <PlatformNode
        platform={PLATFORMS[0]}
        position={sharedPosition}
        onDrag={handleDrag}
        isActive={true}
        budget={totalBudget * allocations.google / 100}
        allocations={allocations}
      />
      
      <Environment preset="city" />
    </>
  );
}

export default function PlatformComparison3D({ apiBase }) {
  const [totalBudget, setTotalBudget] = useState(1000);
  const [allocations, setAllocations] = useState({
    google: 33.3,
    meta: 33.3,
    tiktok: 33.4
  });
  const [goal, setGoal] = useState('purchases');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [view3D, setView3D] = useState(true);

  const runComparison = async () => {
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

  const saveToMemory = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBase}/aria/compare/save`, {
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
        throw new Error(err.detail || 'Save failed');
      }

      const data = await response.json();
      alert(`✅ ${data.message}\n\nAllocation saved as human input decision #${data.decision_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white p-8">
      <div className="w-full px-4">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Platform Comparison Lab
            </h1>
            <p className="text-slate-400">Interactive 3D budget allocation with AI-powered insights</p>
          </div>
          <button
            onClick={() => setView3D(!view3D)}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg transition-all"
          >
            <Maximize2 className="w-4 h-4" />
            {view3D ? '2D View' : '3D View'}
          </button>
        </div>

        <div className="flex flex-col lg:flex-row gap-6 mb-8">
          {/* 3D Visualization */}
          <div className="w-full lg:flex-[2] bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden" style={{ height: '600px' }}>
            {view3D ? (
              <Canvas>
                <Suspense fallback={null}>
                  <Scene
                    allocations={allocations}
                    onAllocationChange={setAllocations}
                    totalBudget={totalBudget}
                  />
                </Suspense>
              </Canvas>
            ) : (
              <div className="h-full flex items-center justify-center p-8">
                <div className="w-full max-w-md space-y-6">
                  {PLATFORMS.map(platform => (
                    <div key={platform.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{platform.emoji}</span>
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
                        onChange={(e) => {
                          const newValue = parseFloat(e.target.value);
                          const others = PLATFORMS.filter(p => p.id !== platform.id);
                          const remaining = 100 - newValue;
                          const ratio = remaining / (allocations[others[0].id] + allocations[others[1].id]);
                          
                          setAllocations({
                            ...allocations,
                            [platform.id]: newValue,
                            [others[0].id]: allocations[others[0].id] * ratio,
                            [others[1].id]: allocations[others[1].id] * ratio
                          });
                        }}
                        className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                        style={{
                          background: `linear-gradient(to right, ${platform.color} 0%, ${platform.color} ${allocations[platform.id]}%, #334155 ${allocations[platform.id]}%, #334155 100%)`
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="w-full lg:flex-1 space-y-6">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-green-400" />
                Campaign Setup
              </h2>
              
              <div className="space-y-4">
                <div>
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

                <div>
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

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <div className="text-sm text-slate-400 mb-2">Current Allocation</div>
                  {PLATFORMS.map(platform => (
                    <div key={platform.id} className="flex justify-between items-center mb-1">
                      <span className="text-sm">{platform.emoji} {platform.name}</span>
                      <span className="font-bold" style={{ color: platform.color }}>
                        {allocations[platform.id].toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>

                <button
                  onClick={runComparison}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 disabled:from-slate-600 disabled:to-slate-700 disabled:cursor-not-allowed rounded-lg px-6 py-3 font-semibold transition-all"
                >
                  {loading ? 'Analyzing...' : '🤖 Run AI Analysis'}
                </button>

                <button
                  onClick={saveToMemory}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-slate-600 disabled:to-slate-700 disabled:cursor-not-allowed rounded-lg px-6 py-3 font-semibold transition-all"
                >
                  {loading ? 'Saving...' : '💾 Save to Memory (Human Input)'}
                </button>

                {error && (
                  <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm">
                    {error}
                  </div>
                )}
              </div>
            </div>

            {view3D && (
              <div className="bg-blue-500/10 border border-blue-500/50 rounded-lg p-4 text-sm text-blue-300">
                <strong>💡 Tip:</strong> Drag the platform spheres in 3D space to adjust budget allocation. The triangle represents all possible combinations.
              </div>
            )}
          </div>
        </div>

        {/* Analysis Results */}
        {analysis && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Platform Metrics */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
              <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-400" />
                AI Performance Analysis
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {analysis.platform_metrics.map(metric => {
                  const platform = PLATFORMS.find(p => p.id === metric.platform);
                  return (
                    <div key={metric.platform} className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                      <div className="flex items-center gap-2 mb-4">
                        <span className="text-2xl">{platform.emoji}</span>
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
                                className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all"
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
                                className="bg-gradient-to-r from-green-500 to-emerald-500 h-2 rounded-full transition-all"
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
                  <Target className="w-5 h-5 text-blue-400" />
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
