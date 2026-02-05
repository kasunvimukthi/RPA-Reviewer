import React, { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Activity, Search, FileCode, Zap, Lock, Server } from 'lucide-react';

const API_URL = "http://localhost:8000";

const RULE_CATEGORIES = [
    { id: "Workflow Design & Structure", label: "Workflow Structure", icon: <Server size={18} /> },
    { id: "Variables & Arguments", label: "Variables & Args", icon: <FileCode size={18} /> },
    { id: "Error Handling & Exception Management", label: "Error Handling", icon: <AlertTriangle size={18} /> },
    { id: "Readability & Maintainability", label: "Readability", icon: <Search size={18} /> },
    { id: "Security & Credentials", label: "Security", icon: <Lock size={18} /> },
    { id: "Testing & Debugging", label: "Testing & Debug", icon: <Zap size={18} /> },
    { id: "Dependencies & Settings", label: "Dependencies", icon: <Activity size={18} /> }
];

function App() {
    const [path, setPath] = useState("");
    const [activeRules, setActiveRules] = useState(RULE_CATEGORIES.map(r => r.id));
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [includeFramework, setIncludeFramework] = useState(true);

    const toggleRule = (id) => {
        setActiveRules(prev =>
            prev.includes(id) ? prev.filter(r => r !== id) : [...prev, id]
        );
    };

    const analyzeProject = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path,
                    active_rules: activeRules,
                    include_framework: includeFramework
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Analysis failed');

            setResult(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container">
            <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
                <h1 style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                    <Activity size={40} color="var(--accent)" />
                    RPA Reviewer
                </h1>
                <p>Automated Code Review & Best Practices Checker</p>
            </header>

            <div className="card" style={{ maxWidth: '800px', margin: '0 auto 2rem' }}>
                <div className="input-group" style={{ marginBottom: '1.5rem' }}>
                    <Search color="var(--text-secondary)" />
                    <input
                        type="text"
                        value={path}
                        onChange={(e) => setPath(e.target.value)}
                        placeholder="Enter UiPath Project Path..."
                    />
                    <button onClick={analyzeProject} disabled={loading}>
                        {loading ? 'Scanning...' : 'Analyze Project'}
                    </button>
                </div>

                <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-secondary)' }}>Code Review Checklist</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                    {RULE_CATEGORIES.map(category => (
                        <label
                            key={category.id}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                cursor: 'pointer',
                                opacity: activeRules.includes(category.id) ? 1 : 0.5,
                                transition: 'opacity 0.2s'
                            }}
                        >
                            <input
                                type="checkbox"
                                checked={activeRules.includes(category.id)}
                                onChange={() => toggleRule(category.id)}
                                style={{ accentColor: 'var(--accent)', width: '1.2rem', height: '1.2rem' }}
                            />
                            <span style={{ color: activeRules.includes(category.id) ? 'var(--accent)' : 'var(--text-secondary)' }}>{category.icon}</span>
                            <span style={{ fontSize: '0.9rem' }}>{category.label}</span>
                        </label>
                    ))}
                </div>

                <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                        <input
                            type="checkbox"
                            checked={includeFramework}
                            onChange={(e) => setIncludeFramework(e.target.checked)}
                            style={{ accentColor: 'var(--accent)', width: '1.2rem', height: '1.2rem' }}
                        />
                        <span style={{ fontSize: '0.9rem', fontWeight: '500' }}>Include REFramework default workflows</span>
                    </label>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginLeft: '1.95rem', marginTop: '0.25rem' }}>
                        If disabled, files like Main.xaml, Process.xaml, and InitAllSettings.xaml will be skipped.
                    </p>
                </div>

                {error && <div style={{ color: 'var(--danger)', marginTop: '1rem' }}>⚠️ {error}</div>}
            </div>

            {result && (
                <div className="results">
                    {/* Stats Summary */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                        <div className="card" style={{ textAlign: 'center', borderColor: 'var(--success)', background: 'rgba(16, 185, 129, 0.1)' }}>
                            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Passed Checks</div>
                            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--success)' }}>{result.stats.pass_count}</div>
                        </div>
                        <div className="card" style={{ textAlign: 'center', borderColor: 'var(--danger)', background: 'rgba(239, 68, 68, 0.1)' }}>
                            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Failed Checks</div>
                            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--danger)' }}>{result.stats.fail_count}</div>
                        </div>
                        <div className="card" style={{ textAlign: 'center', borderColor: 'var(--accent)' }}>
                            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Overall Compliance</div>
                            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                                {result.stats.overall_percentage}%
                            </div>
                        </div>
                    </div>

                    {result.areas.map((area, idx) => (
                        <div key={idx} className="card" style={{ marginBottom: '2rem' }}>
                            <h2>{area.name}</h2>
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>Checkpoint</th>
                                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>Status</th>
                                        <th style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>Comment</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {area.checkpoints.map((cp, cIdx) => (
                                        <tr key={cIdx} style={{ borderBottom: '1px solid var(--border)' }}>
                                            <td style={{ padding: '0.75rem', width: '40%' }}>{cp.question}</td>
                                            <td style={{ padding: '0.75rem', width: '10%' }}>
                                                <span className={`badge ${cp.status}`} style={{
                                                    backgroundColor: cp.status === 'PASS' ? 'rgba(16, 185, 129, 0.2)' :
                                                        cp.status === 'FAIL' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                                                    color: cp.status === 'PASS' ? 'var(--success)' :
                                                        cp.status === 'FAIL' ? 'var(--danger)' : 'var(--text-secondary)',
                                                    border: `1px solid ${cp.status === 'PASS' ? 'rgba(16, 185, 129, 0.4)' :
                                                        cp.status === 'FAIL' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(148, 163, 184, 0.4)'}`
                                                }}>
                                                    {cp.status}
                                                </span>
                                            </td>
                                            <td style={{ padding: '0.75rem', color: 'var(--text-secondary)', fontSize: '0.9rem', whiteSpace: 'pre-line' }}>
                                                {cp.comment}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function StatCard({ label, value, icon, color }) {
    return (
        <div className="card" style={{ textAlign: 'center', borderColor: color }}>
            <div style={{ color: color, marginBottom: '0.5rem', display: 'flex', justifyContent: 'center' }}>
                {React.cloneElement(icon, { size: 32 })}
            </div>
            <div className="stat-value" style={{ color: color }}>{value}</div>
            <div className="stat-label">{label}</div>
        </div>
    );
}

function ScoreItem({ label, value, icon }) {
    const width = `${value * 10}%`;
    const color = getScoreColor(value);

    return (
        <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {icon} {label}
                </span>
                <span style={{ fontWeight: 'bold', color: color }}>{value}/10</span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
                <div style={{ width, height: '100%', background: color, borderRadius: '4px', transition: 'width 1s ease' }}></div>
            </div>
        </div>
    );
}

function getScoreColor(score) {
    if (score >= 8) return 'var(--success)';
    if (score >= 5) return 'var(--warning)';
    return 'var(--danger)';
}

export default App;
