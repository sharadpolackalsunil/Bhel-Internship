import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API = 'http://localhost:8001/api'

export default function Students() {
  const [students, setStudents] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetch(`${API}/students`)
      .then(r => r.json())
      .then(data => {
        setStudents(data.students || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner"></div>
      </div>
    )
  }

  const filtered = students.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.enrollment.toLowerCase().includes(search.toLowerCase()) ||
    (s.branch || '').toLowerCase().includes(search.toLowerCase())
  )

  const getInitials = (name) => {
    if (!name) return '?'
    return name.split(' ').map(w => w[0]).slice(0, 2).join('')
  }

  return (
    <>
      <div className="page-header fade-in">
        <h2>👥 Student Profiles</h2>
        <p>IUMS Portal — Personal details, fee status, and academic history</p>
      </div>

      <div className="search-bar fade-in delay-1">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          placeholder="Search by name, enrollment, or branch..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state fade-in delay-2">
          <div className="empty-icon">📭</div>
          <p>No students found. Make sure you've run the IUMS scraper first.</p>
        </div>
      ) : (
        <div className="students-grid fade-in delay-2">
          {filtered.map(s => (
            <div
              key={s.enrollment}
              className="student-card"
              onClick={() => navigate(`/student/${s.enrollment}`)}
            >
              <div className="student-avatar">{getInitials(s.name)}</div>
              <div className="student-name">{s.name || 'Unknown'}</div>
              <div className="student-enrollment">{s.enrollment}</div>
              <span className="student-branch-tag">
                {s.branch || s.programme || 'N/A'}
              </span>
              {s.cgpa && (
                <div className="student-cgpa">{s.cgpa.toFixed(2)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  )
}
