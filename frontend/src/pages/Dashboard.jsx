import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts'

const API = 'http://localhost:8001/api'

const COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

export default function Dashboard() {
  const [results, setResults] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API}/results`).then(r => r.json()),
      fetch(`${API}/analytics`).then(r => r.json()),
    ]).then(([resData, analyticsData]) => {
      setResults(resData.results || [])
      setAnalytics(analyticsData)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner"></div>
      </div>
    )
  }

  const filtered = results.filter(r =>
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    r.enrollment.toLowerCase().includes(search.toLowerCase()) ||
    r.branch.toLowerCase().includes(search.toLowerCase())
  )

  // Prepare chart data
  const sgpaDistData = analytics?.sgpa_distribution
    ? Object.entries(analytics.sgpa_distribution).map(([range, count]) => ({
        range,
        count,
      }))
    : []

  const branchAvgData = analytics?.branch_averages
    ? Object.entries(analytics.branch_averages).map(([branch, data]) => ({
        branch: branch.replace('AI_', ''),
        avg_sgpa: data.avg_sgpa,
        students: data.total_students,
        pass: data.pass_count,
        fail: data.fail_count,
      }))
    : []

  const passFailData = analytics?.branch_averages
    ? Object.entries(analytics.branch_averages).map(([branch, data]) => ({
        name: branch.replace('AI_', ''),
        pass: data.pass_count,
        fail: data.fail_count,
      }))
    : []

  // ── Extra analytics ──
  const allSgpas = results.map(r => r.sgpa).filter(s => s != null)
  const highestSgpa = allSgpas.length ? Math.max(...allSgpas) : null
  const lowestSgpa = allSgpas.length ? Math.min(...allSgpas) : null
  const medianSgpa = (() => {
    if (!allSgpas.length) return null
    const sorted = [...allSgpas].sort((a, b) => a - b)
    const mid = Math.floor(sorted.length / 2)
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
  })()
  const graceCount = results.filter(r => r.result_status && r.result_status.toUpperCase().includes('GRACE')).length
  const failCount = results.filter(r => r.result_status && r.result_status.toUpperCase().includes('FAIL')).length
  const above8 = allSgpas.filter(s => s >= 8).length
  const below5 = allSgpas.filter(s => s < 5).length

  // Bottom 5 at-risk students
  const bottom5 = [...results]
    .filter(r => r.sgpa != null)
    .sort((a, b) => (a.sgpa || 0) - (b.sgpa || 0))
    .slice(0, 5)

  // Branch-wise pass/fail stacked data
  const branchPassFailData = branchAvgData.map(b => ({
    branch: b.branch,
    Pass: b.pass,
    Fail: b.fail,
  }))

  // Radar chart data for branch comparison
  const radarData = branchAvgData.map(b => ({
    branch: b.branch,
    'Avg SGPA': b.avg_sgpa,
    'Pass Rate': b.students ? Math.round((b.pass / b.students) * 10) : 0,
    'Students': Math.min(b.students / 10, 10),
  }))

  const getBadgeClass = (status) => {
    if (!status) return ''
    const s = status.toUpperCase()
    if (s.includes('FAIL')) return 'fail'
    if (s.includes('GRACE')) return 'grace'
    return 'pass'
  }

  return (
    <>
      <div className="page-header fade-in">
        <h2>📊 Results & Analytics</h2>
        <p>AI Department — Semester 4 Performance Overview</p>
      </div>

      {/* ── Stat Cards ── */}
      <div className="stats-grid fade-in delay-1">
        <div className="stat-card purple">
          <div className="stat-label">Total Students</div>
          <div className="stat-value">{analytics?.total_students || 0}</div>
        </div>
        <div className="stat-card teal">
          <div className="stat-label">Avg SGPA</div>
          <div className="stat-value">
            {branchAvgData.length
              ? (branchAvgData.reduce((s, b) => s + b.avg_sgpa * b.students, 0) /
                 branchAvgData.reduce((s, b) => s + b.students, 0)).toFixed(2)
              : '—'}
          </div>
          <div className="stat-sub">Median: {medianSgpa?.toFixed(2) || '—'}</div>
        </div>
        <div className="stat-card green">
          <div className="stat-label">Pass Rate</div>
          <div className="stat-value">
            {branchAvgData.length
              ? Math.round(
                  (branchAvgData.reduce((s, b) => s + b.pass, 0) /
                   branchAvgData.reduce((s, b) => s + b.students, 0)) * 100
                ) + '%'
              : '—'}
          </div>
          <div className="stat-sub">{graceCount} with grace</div>
        </div>
        <div className="stat-card orange">
          <div className="stat-label">Highest SGPA</div>
          <div className="stat-value">{highestSgpa?.toFixed(2) || '—'}</div>
          <div className="stat-sub">Lowest: {lowestSgpa?.toFixed(2) || '—'}</div>
        </div>
      </div>

      {/* ── Quick Insight Cards ── */}
      <div className="stats-grid fade-in delay-1" style={{ marginTop: -12 }}>
        <div className="stat-card purple">
          <div className="stat-label">Above 8.0 SGPA</div>
          <div className="stat-value">{above8}</div>
          <div className="stat-sub">{allSgpas.length ? Math.round((above8 / allSgpas.length) * 100) : 0}% of class</div>
        </div>
        <div className="stat-card teal">
          <div className="stat-label">Below 5.0 SGPA</div>
          <div className="stat-value">{below5}</div>
          <div className="stat-sub">{allSgpas.length ? Math.round((below5 / allSgpas.length) * 100) : 0}% at risk</div>
        </div>
        <div className="stat-card green">
          <div className="stat-label">Failed Students</div>
          <div className="stat-value">{failCount}</div>
        </div>
        <div className="stat-card orange">
          <div className="stat-label">Branches</div>
          <div className="stat-value">{Object.keys(analytics?.branch_averages || {}).length}</div>
        </div>
      </div>

      {/* ── Charts ── */}
      <div className="charts-grid fade-in delay-2">
        {/* SGPA Distribution */}
        <div className="chart-card">
          <h3>📈 SGPA Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={sgpaDistData}>
              <defs>
                <linearGradient id="sgpaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
              <XAxis dataKey="range" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: '#fff', border: '1px solid #e0e7ff',
                  borderRadius: 12, boxShadow: '0 4px 14px rgba(0,0,0,0.08)'
                }}
              />
              <Area type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2.5}
                fill="url(#sgpaGrad)" name="Students" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Branch Average */}
        <div className="chart-card">
          <h3>🏆 Branch-wise Average SGPA</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={branchAvgData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
              <XAxis dataKey="branch" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: '#fff', border: '1px solid #e0e7ff',
                  borderRadius: 12, boxShadow: '0 4px 14px rgba(0,0,0,0.08)'
                }}
              />
              <Bar dataKey="avg_sgpa" name="Avg SGPA" radius={[6, 6, 0, 0]}>
                {branchAvgData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pass/Fail Pie */}
        <div className="chart-card">
          <h3>✅ Pass vs Fail</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={[
                  { name: 'Pass', value: passFailData.reduce((s, b) => s + b.pass, 0) },
                  { name: 'Fail', value: passFailData.reduce((s, b) => s + b.fail, 0) },
                  { name: 'Grace', value: graceCount },
                ]}
                cx="50%" cy="50%"
                outerRadius={90}
                innerRadius={50}
                paddingAngle={4}
                dataKey="value"
                label={({ name, percent }) => percent > 0.01 ? `${name} ${(percent * 100).toFixed(0)}%` : ''}
              >
                <Cell fill="#22c55e" />
                <Cell fill="#ef4444" />
                <Cell fill="#f59e0b" />
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Branch Pass/Fail Stacked Bar */}
        <div className="chart-card">
          <h3>📊 Branch-wise Pass / Fail Split</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={branchPassFailData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.1)" />
              <XAxis dataKey="branch" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: '#fff', border: '1px solid #e0e7ff',
                  borderRadius: 12, boxShadow: '0 4px 14px rgba(0,0,0,0.08)'
                }}
              />
              <Legend />
              <Bar dataKey="Pass" stackId="a" fill="#22c55e" radius={[0, 0, 0, 0]} />
              <Bar dataKey="Fail" stackId="a" fill="#ef4444" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Row 2: Top 10 + Bottom 5 + Radar ── */}
      <div className="charts-grid fade-in delay-2" style={{ marginTop: 0 }}>
        {/* Top 10 */}
        <div className="chart-card">
          <h3>🥇 Top 10 — Department</h3>
          <div className="top-students-list">
            {(analytics?.top10_department || []).map((s, i) => (
              <div className="top-student-item" key={s.enrollment}>
                <div className={`top-student-rank ${i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'normal'}`}>
                  {i + 1}
                </div>
                <div className="top-student-info">
                  <div className="top-student-name">{s.name}</div>
                  <div className="top-student-branch">{s.branch}</div>
                </div>
                <div className="top-student-sgpa">{s.sgpa?.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom 5 At Risk */}
        <div className="chart-card">
          <h3>⚠️ Bottom 5 — At Risk</h3>
          <div className="top-students-list">
            {bottom5.map((s, i) => (
              <div className="top-student-item" key={s.enrollment}>
                <div className="top-student-rank" style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)', color: '#fff' }}>
                  {i + 1}
                </div>
                <div className="top-student-info">
                  <div className="top-student-name">{s.name}</div>
                  <div className="top-student-branch">{s.branch}</div>
                </div>
                <div className="top-student-sgpa" style={{ color: '#ef4444' }}>{s.sgpa?.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Top 5 per Branch Cards ── */}
      {analytics?.top5_per_branch && (
        <div className="fade-in delay-3" style={{ marginBottom: 32 }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 16 }}>
            🌟 Top 5 Per Branch
          </h3>
          <div className="charts-grid">
            {Object.entries(analytics.top5_per_branch).map(([branch, students]) => (
              <div className="chart-card" key={branch}>
                <h3 style={{ fontSize: '0.9rem' }}>
                  {branch === 'AI_DS' ? 'AI & Data Science' : branch === 'AI_ML' ? 'AI & Machine Learning' : 'Artificial Intelligence'}
                </h3>
                <div className="top-students-list">
                  {students.map((s, i) => (
                    <div className="top-student-item" key={s.enrollment}>
                      <div className={`top-student-rank ${i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : 'normal'}`}>
                        {i + 1}
                      </div>
                      <div className="top-student-info">
                        <div className="top-student-name">{s.name}</div>
                      </div>
                      <div className="top-student-sgpa">{s.sgpa?.toFixed(2)}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Results Table ── */}
      <div className="fade-in delay-3">
        <div className="search-bar">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search by name, enrollment, or branch..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Enrollment</th>
                <th>Name</th>
                <th>Branch</th>
                <th>SGPA</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 50).map(r => (
                <tr key={r.enrollment}>
                  <td>{r.rank || '—'}</td>
                  <td style={{ fontWeight: 600, color: '#6366f1' }}>{r.enrollment}</td>
                  <td>{r.name}</td>
                  <td>
                    <span className="student-branch-tag" style={{ fontSize: '0.72rem' }}>
                      {r.branch_code || r.branch}
                    </span>
                  </td>
                  <td style={{ fontWeight: 700 }}>{r.sgpa?.toFixed(2) || '—'}</td>
                  <td>
                    <span className={`badge ${getBadgeClass(r.result_status)}`}>
                      {r.result_status?.replace('FAIL IN SUBJECTS ', 'FAIL')?.substring(0, 20) || '—'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length > 50 && (
          <p style={{ textAlign: 'center', padding: 16, color: '#94a3b8', fontSize: '0.85rem' }}>
            Showing 50 of {filtered.length} results. Refine your search to see more.
          </p>
        )}
      </div>
    </>
  )
}
