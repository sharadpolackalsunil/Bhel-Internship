import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine
} from 'recharts'

const API = 'http://localhost:8001/api'

export default function StudentDetail() {
  const { enrollment } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/student/${enrollment}`)
      .then(r => r.json())
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [enrollment])

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner"></div>
      </div>
    )
  }

  if (!data || !data.profile) {
    return (
      <div className="empty-state">
        <div className="empty-icon">❌</div>
        <p>Student not found</p>
        <button className="back-btn" onClick={() => navigate('/students')}>
          ← Back to Students
        </button>
      </div>
    )
  }

  const { profile, fees, academic, cgpa } = data

  // Compute growth insight
  const growthInsight = (() => {
    if (!academic || academic.length < 2) return null
    const latest = academic[academic.length - 1]
    const previous = academic[academic.length - 2]
    if (!latest?.sgpa || !previous?.sgpa) return null
    const diff = latest.sgpa - previous.sgpa
    return {
      diff: Math.abs(diff).toFixed(2),
      direction: diff >= 0 ? 'up' : 'down',
      label: diff >= 0 ? 'Improvement' : 'Decline',
    }
  })()

  // Chart data (semester by semester)
  let cumSum = 0
  let count = 0
  const chartData = (academic || []).map(a => {
    if (a.sgpa) {
      cumSum += a.sgpa
      count += 1
    }
    return {
      sem: `Sem ${a.semester}`,
      sgpa: a.sgpa,
      running_cgpa: count > 0 ? cumSum / count : null,
      session: a.session,
    }
  })

  // Compute dynamic Y-axis domain so chart is zoomed into the data range
  const allValues = chartData.flatMap(d => [d.sgpa, d.running_cgpa]).filter(Boolean)
  const minSgpa = allValues.length ? Math.min(...allValues) : 0
  const maxSgpa = allValues.length ? Math.max(...allValues) : 10
  const yMin = Math.max(0, minSgpa - 0.2)
  const yMax = Math.min(10, maxSgpa + 0.2)

  // Best & worst semester
  const bestSem = academic && academic.length
    ? academic.reduce((best, a) => (a.sgpa || 0) > (best.sgpa || 0) ? a : best, academic[0])
    : null
  const worstSem = academic && academic.length
    ? academic.reduce((worst, a) => (a.sgpa || 0) < (worst.sgpa || 0) ? a : worst, academic[0])
    : null

  // Per-semester change
  const semChanges = chartData.map((d, i) => {
    if (i === 0) return { ...d, change: null }
    const prev = chartData[i - 1].sgpa || 0
    const curr = d.sgpa || 0
    return { ...d, change: curr - prev }
  })

  return (
    <>
      <button className="back-btn fade-in" onClick={() => navigate('/students')}>
        ← Back to Students
      </button>

      {/* ── Profile Header ── */}
      <div className="profile-header fade-in delay-1">
        <div className="profile-name">{profile.name}</div>
        <div className="profile-enrollment">{enrollment} • {profile.programme}</div>
        <div className="profile-meta">
          <div className="profile-meta-item">
            <span className="meta-label">Branch</span>
            <span className="meta-value">{profile.branch || '—'}</span>
          </div>
          <div className="profile-meta-item">
            <span className="meta-label">Gender</span>
            <span className="meta-value">{profile.gender || '—'}</span>
          </div>
          <div className="profile-meta-item">
            <span className="meta-label">DOB</span>
            <span className="meta-value">{profile.dob || '—'}</span>
          </div>
          <div className="profile-meta-item">
            <span className="meta-label">Admission Year</span>
            <span className="meta-value">{profile.admission_year || '—'}</span>
          </div>
          {cgpa && (
            <div className="profile-meta-item">
              <span className="meta-label">Current CGPA</span>
              <span className="meta-value" style={{ fontSize: '1.4rem', fontWeight: 900 }}>
                {cgpa.toFixed(2)}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── SGPA Growth Chart ── */}
      {chartData.length > 0 && (
        <div className="chart-card fade-in delay-2" style={{ marginBottom: 24 }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            📈 SGPA Growth Trajectory
            {growthInsight && (
              <span className={`growth-indicator ${growthInsight.direction}`}>
                {growthInsight.direction === 'up' ? '▲' : '▼'} {growthInsight.diff} {growthInsight.label}
              </span>
            )}
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData}>
              <defs>
                <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
              <XAxis dataKey="sem" tick={{ fontSize: 13, fontWeight: 600 }} />
              <YAxis domain={[yMin, yMax]} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: '#fff', border: '1px solid #e0e7ff',
                  borderRadius: 12, boxShadow: '0 4px 14px rgba(0,0,0,0.08)'
                }}
                formatter={(value, name) => [value?.toFixed(2), name === 'sgpa' ? 'SGPA' : 'Running CGPA']}
                labelFormatter={(label) => {
                  const item = chartData.find(d => d.sem === label)
                  return `${label} — ${item?.session || ''}`
                }}
              />
              <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '13px', fontWeight: 600 }} />
              {/* Removed Final CGPA Reference Line */}
              <Line
                name="SGPA"
                type="monotone"
                dataKey="sgpa"
                stroke="#6366f1"
                strokeWidth={3}
                dot={{ r: 6, fill: '#6366f1', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 8, fill: '#4f46e5' }}
              />
              <Line
                name="Running CGPA"
                type="monotone"
                dataKey="running_cgpa"
                stroke="#f59e0b"
                strokeWidth={3}
                dot={{ r: 6, fill: '#f59e0b', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 8, fill: '#d97706' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Semester-by-Semester Growth + Best/Worst ── */}
      {academic && academic.length > 1 && (
        <div className="stats-grid fade-in delay-2" style={{ marginBottom: 24 }}>
          {bestSem && (
            <div className="stat-card green">
              <div className="stat-label">🏆 Best Semester</div>
              <div className="stat-value">{bestSem.sgpa?.toFixed(2)}</div>
              <div className="stat-sub">Sem {bestSem.semester} — {bestSem.session}</div>
            </div>
          )}
          {worstSem && (
            <div className="stat-card orange">
              <div className="stat-label">📉 Weakest Semester</div>
              <div className="stat-value">{worstSem.sgpa?.toFixed(2)}</div>
              <div className="stat-sub">Sem {worstSem.semester} — {worstSem.session}</div>
            </div>
          )}
          <div className="stat-card purple">
            <div className="stat-label">Total Semesters</div>
            <div className="stat-value">{academic.length}</div>
            <div className="stat-sub">All {academic.every(a => a.result?.toUpperCase() === 'PASS') ? 'PASSED ✓' : 'with some backlogs'}</div>
          </div>
          <div className="stat-card teal">
            <div className="stat-label">SGPA Range</div>
            <div className="stat-value">{minSgpa.toFixed(2)} — {maxSgpa.toFixed(2)}</div>
            <div className="stat-sub">Spread: {(maxSgpa - minSgpa).toFixed(2)} pts</div>
          </div>
        </div>
      )}

      {/* ── CGPA + Growth Highlight ── */}
      <div className="profile-sections fade-in delay-2">
        {cgpa && (
          <div className="cgpa-highlight">
            <div className="cgpa-value">{cgpa.toFixed(2)}</div>
            <div className="cgpa-label">Overall CGPA</div>
            {growthInsight && (
              <div style={{ marginTop: 8, fontSize: '0.85rem', opacity: 0.85 }}>
                {growthInsight.direction === 'up' ? '📈' : '📉'}{' '}
                {growthInsight.diff} points {growthInsight.label.toLowerCase()} from last semester
              </div>
            )}
          </div>
        )}

        {/* ── Personal Details ── */}
        <div className="section-card">
          <h3>👤 Personal Details</h3>
          <div className="info-grid">
            <InfoItem label="Father's Name" value={profile.father} />
            <InfoItem label="Mother's Name" value={profile.mother} />
            <InfoItem label="Category" value={profile.category} />
            <InfoItem label="Email" value={profile.email} />
            <InfoItem label="Phone" value={profile.phone} />
            <InfoItem label="City" value={profile.city} />
            <InfoItem label="State" value={profile.state} />
            <InfoItem label="Pincode" value={profile.pincode} />
          </div>
          {profile.address && (
            <div style={{ marginTop: 16 }}>
              <InfoItem label="Address" value={profile.address} />
            </div>
          )}
        </div>
      </div>

      {/* ── Fee Status + Academic History ── */}
      <div className="profile-sections fade-in delay-3">
        {/* Fee Status */}
        <div className="section-card">
          <h3>💰 Fee Status</h3>
          {fees && fees.length > 0 ? (
            <div className="fee-timeline">
              {fees.map((f, i) => (
                <div className="fee-item" key={i}>
                  <div className="fee-sem">{f.semester}</div>
                  <div className="fee-year">{f.year}</div>
                  <span className={`badge ${f.status?.toLowerCase().includes('submitted') ? 'paid' : 'unpaid'}`}>
                    {f.status || 'Unknown'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No fee data available</p>
          )}
        </div>

        {/* Academic History */}
        <div className="section-card">
          <h3>🎓 Academic History</h3>
          {academic && academic.length > 0 ? (
            <div className="data-table-wrapper" style={{ border: 'none', boxShadow: 'none' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Sem</th>
                    <th>Session</th>
                    <th>SGPA</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {academic.map((a, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 700 }}>{a.semester}</td>
                      <td style={{ fontSize: '0.82rem', color: '#64748b' }}>{a.session}</td>
                      <td style={{ fontWeight: 800, color: '#6366f1', fontSize: '1.05rem' }}>
                        {a.sgpa?.toFixed(2)}
                      </td>
                      <td>
                        <span className={`badge ${a.result?.toUpperCase() === 'PASS' ? 'pass' : 'fail'}`}>
                          {a.result}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No academic data available</p>
          )}
        </div>
      </div>
    </>
  )
}

function InfoItem({ label, value }) {
  return (
    <div className="info-item">
      <div className="info-label">{label}</div>
      <div className="info-value">{value || '—'}</div>
    </div>
  )
}
