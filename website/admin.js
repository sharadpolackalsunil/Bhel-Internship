/* ============================================================
   Admin Dashboard — Logic
   Login, analytics rendering, sortable table, profile modal
   ============================================================ */

const ADMIN_PASSWORD = 'BHEL123';

let sortField = 'rank';
let sortDirection = 'asc';
let filteredStudents = [];

// ── Admin Login ──
function handleAdminLogin(e) {
  e.preventDefault();
  const password = document.getElementById('adminPasswordInput').value;
  const errorEl = document.getElementById('adminLoginError');

  if (password !== ADMIN_PASSWORD) {
    errorEl.classList.add('show');
    errorEl.textContent = 'Incorrect password. Please try again.';
    return false;
  }

  errorEl.classList.remove('show');
  document.getElementById('adminLoginSection').style.display = 'none';
  document.getElementById('adminDashboard').classList.add('active');

  renderAdminDashboard();
  return false;
}

function adminLogout() {
  document.getElementById('adminDashboard').classList.remove('active');
  document.getElementById('adminLoginSection').style.display = '';
  document.getElementById('adminPasswordInput').value = '';
}

// ── Render Dashboard ──
function renderAdminDashboard() {
  renderOverviewCards();
  renderBranchChart();
  renderHistogram();
  renderPassRateChart();
  renderTopPerformers();
  renderAllStudentsTable();
  setupTableControls();
}

// ── Overview Cards ──
function renderOverviewCards() {
  const grid = document.getElementById('overviewGrid');
  const cards = [
    { icon: '👥', iconBg: 'rgba(102,126,234,0.15)', value: STATS.total, label: 'Total Students' },
    { icon: '✅', iconBg: 'rgba(16,185,129,0.15)', value: STATS.passRate + '%', label: 'Pass Rate' },
    { icon: '📊', iconBg: 'rgba(6,182,212,0.15)', value: STATS.avgSGPA.toFixed(2), label: 'Average SGPA' },
    { icon: '🏆', iconBg: 'rgba(249,159,28,0.15)', value: STATS.maxSGPA.toFixed(2), label: 'Highest SGPA' },
  ];

  grid.innerHTML = cards.map(c => `
    <div class="glass-card overview-card">
      <div class="overview-icon" style="background:${c.iconBg};">${c.icon}</div>
      <div class="overview-info">
        <h3>${c.value}</h3>
        <p>${c.label}</p>
      </div>
    </div>
  `).join('');
}

// ── Branch Average SGPA Chart ──
function renderBranchChart() {
  const container = document.getElementById('branchBarChart');
  const branches = STATS.branches;
  const maxSGPA = 10;

  container.innerHTML = Object.keys(branches).map(bc => {
    const b = branches[bc];
    const widthPct = (b.avgSGPA / maxSGPA * 100).toFixed(1);
    return `
      <div class="bar-row">
        <div class="bar-label">${bc}</div>
        <div class="bar-track">
          <div class="bar-fill" data-width="${widthPct}%" style="width:0%;">${b.avgSGPA.toFixed(2)}</div>
        </div>
        <div class="bar-value">${b.count} students</div>
      </div>
    `;
  }).join('');

  // Animate bars
  setTimeout(() => {
    container.querySelectorAll('.bar-fill').forEach(bar => {
      bar.style.width = bar.getAttribute('data-width');
    });
  }, 300);
}

// ── SGPA Histogram ──
function renderHistogram() {
  const container = document.getElementById('sgpaHistogram');
  const dist = STATS.distribution;
  const maxCount = Math.max(...Object.values(dist), 1);

  container.innerHTML = Object.keys(dist).map(bucket => {
    const count = dist[bucket];
    const heightPct = (count / maxCount * 100).toFixed(1);
    return `
      <div class="histogram-bar-wrap">
        <div class="histogram-bar" style="height:${heightPct}%;">
          ${count > 0 ? `<div class="hist-count">${count}</div>` : ''}
        </div>
        <div class="histogram-label">${bucket}</div>
      </div>
    `;
  }).join('');
}

// ── Pass Rate by Branch ──
function renderPassRateChart() {
  const container = document.getElementById('passRateChart');
  const branches = STATS.branches;

  container.innerHTML = Object.keys(branches).map(bc => {
    const b = branches[bc];
    return `
      <div class="bar-row">
        <div class="bar-label">${bc}</div>
        <div class="bar-track">
          <div class="bar-fill" data-width="${b.passRate}%" style="width:0%; background:linear-gradient(135deg, #10b981, #059669);">${b.passRate}%</div>
        </div>
        <div class="bar-value">${b.passed}/${b.count}</div>
      </div>
    `;
  }).join('');

  setTimeout(() => {
    container.querySelectorAll('.bar-fill').forEach(bar => {
      bar.style.width = bar.getAttribute('data-width');
    });
  }, 500);
}

// ── Top Performers ──
function renderTopPerformers() {
  const tbody = document.getElementById('topPerformersBody');
  const top10 = STUDENTS
    .filter(s => s.sgpa != null)
    .sort((a, b) => b.sgpa - a.sgpa)
    .slice(0, 10);

  tbody.innerHTML = top10.map((s, i) => `
    <tr onclick="openStudentProfile('${s.enrollment}')" style="cursor:pointer;">
      <td><span style="font-weight:800; color:${i < 3 ? 'var(--accent-amber)' : 'var(--text-secondary)'};">${i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i + 1)}</span></td>
      <td style="font-weight:600;">${s.name}</td>
      <td style="font-family:var(--font-mono); font-size:0.8rem;">${s.enrollment}</td>
      <td><span class="status-badge" style="background:rgba(102,126,234,0.1); color:var(--accent-blue);">${s.branchCode}</span></td>
      <td class="sgpa-value ${sgpaColorClass(s.sgpa)}">${s.sgpa.toFixed(2)}</td>
      <td><span class="status-badge ${s.result === 'PASS' ? 'pass' : 'fail'}">${s.result}</span></td>
    </tr>
  `).join('');
}

// ── All Students Table ──
function renderAllStudentsTable() {
  filteredStudents = [...STUDENTS];
  applyFiltersAndSort();
}

function applyFiltersAndSort() {
  const search = (document.getElementById('studentSearch')?.value || '').toLowerCase();
  const branchFilter = document.getElementById('branchFilter')?.value || '';
  const statusFilter = document.getElementById('statusFilter')?.value || '';

  filteredStudents = STUDENTS.filter(s => {
    const matchSearch = !search || 
      s.name.toLowerCase().includes(search) || 
      s.enrollment.toLowerCase().includes(search);
    const matchBranch = !branchFilter || s.branchCode === branchFilter;
    const matchStatus = !statusFilter || s.result === statusFilter;
    return matchSearch && matchBranch && matchStatus;
  });

  // Sort
  filteredStudents.sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];

    // Handle nulls
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;

    // Numeric vs string
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    }

    aVal = String(aVal).toLowerCase();
    bVal = String(bVal).toLowerCase();
    if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
    return 0;
  });

  renderTableRows();
}

function renderTableRows() {
  const tbody = document.getElementById('allStudentsBody');
  
  tbody.innerHTML = filteredStudents.map(s => `
    <tr onclick="openStudentProfile('${s.enrollment}')">
      <td style="font-weight:700; color:var(--text-muted);">${s.rank != null ? s.rank : '—'}</td>
      <td style="font-weight:600;">${s.name}</td>
      <td style="font-family:var(--font-mono); font-size:0.8rem;">${s.enrollment}</td>
      <td><span class="status-badge" style="background:rgba(102,126,234,0.1); color:var(--accent-blue);">${s.branchCode}</span></td>
      <td class="sgpa-value ${s.sgpa != null ? sgpaColorClass(s.sgpa) : ''}">${s.sgpa != null ? s.sgpa.toFixed(2) : '—'}</td>
      <td><span class="status-badge ${s.result === 'PASS' ? 'pass' : s.result === 'FAIL' ? 'fail' : 'not-found'}">${s.result}</span></td>
      <td><button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); openStudentProfile('${s.enrollment}')">View →</button></td>
    </tr>
  `).join('');

  document.getElementById('tableInfo').textContent = `Showing ${filteredStudents.length} of ${STUDENTS.length} students`;
}

// ── Table Controls ──
function setupTableControls() {
  // Search
  document.getElementById('studentSearch')?.addEventListener('input', applyFiltersAndSort);
  document.getElementById('branchFilter')?.addEventListener('change', applyFiltersAndSort);
  document.getElementById('statusFilter')?.addEventListener('change', applyFiltersAndSort);

  // Sortable headers
  document.querySelectorAll('#allStudentsTable th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const field = th.dataset.sort;
      if (sortField === field) {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
      } else {
        sortField = field;
        sortDirection = field === 'sgpa' ? 'desc' : 'asc';
      }
      applyFiltersAndSort();
    });
  });
}

// ── Student Profile Modal ──
function openStudentProfile(enrollment) {
  const student = STUDENTS.find(s => s.enrollment === enrollment);
  if (!student) return;

  const modal = document.getElementById('profileModal');
  const content = document.getElementById('profileContent');

  const initials = (student.name || '').split(' ').map(w => w[0]).join('').slice(0, 2);
  const subjects = student.subjects || [];

  // Count total credits
  const totalCredits = subjects.reduce((sum, s) => sum + (parseInt(s.tc) || 0), 0);
  const earnedCredits = subjects.reduce((sum, s) => sum + (parseInt(s.ec) || 0), 0);

  // Grade distribution
  const gradeCounts = {};
  subjects.forEach(s => {
    const g = (s.grade || 'Other').toUpperCase();
    gradeCounts[g] = (gradeCounts[g] || 0) + 1;
  });

  content.innerHTML = `
    <button class="profile-close" onclick="closeProfile()">✕</button>
    
    <div class="profile-header-info">
      <div class="profile-avatar">${initials}</div>
      <div>
        <div class="profile-name">${student.name}</div>
        <div class="profile-enrollment">${student.enrollment}</div>
      </div>
    </div>

    <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1.5rem; padding:1rem; background:rgba(102,126,234,0.05); border-radius:var(--radius-md); border:1px solid rgba(102,126,234,0.15);">
      <span style="font-size:0.8rem; color:var(--text-muted); display:flex; align-items:center; margin-right:0.5rem;">🌐 MITS Portal:</span>
      <a href="https://iums.mitsgwalior.in/StudentLife/Student_UploadPhoto.aspx?url=Student%20Profile" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">👤 Student Profile</a>
      <a href="https://iums.mitsgwalior.in/StudentLife/AcademicHistory.aspx" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">🎓 Academic History</a>
      <a href="https://iums.mitsgwalior.in/StudentLife/ViewAttendance.aspx" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">📊 Attendance</a>
      <a href="https://iums.mitsgwalior.in/StudentLife/Studenthome.aspx" target="_blank" rel="noopener" class="btn btn-ghost btn-sm">📚 Services</a>
    </div>

    <div class="profile-section">
      <h3>Personal Information</h3>
      <div class="profile-info-grid">
        <div class="profile-field">
          <span class="field-label">Full Name</span>
          <span class="field-value">${student.name}</span>
        </div>
        <div class="profile-field">
          <span class="field-label">Enrollment No.</span>
          <span class="field-value" style="font-family:var(--font-mono);">${student.enrollment}</span>
        </div>
        <div class="profile-field">
          <span class="field-label">Branch</span>
          <span class="field-value">${student.branch}</span>
        </div>
        <div class="profile-field">
          <span class="field-label">Semester</span>
          <span class="field-value">${student.semester || '4'}</span>
        </div>
        <div class="profile-field">
          <span class="field-label">Program</span>
          <span class="field-value">B.Tech</span>
        </div>
        <div class="profile-field">
          <span class="field-label">Status</span>
          <span class="field-value">${student.status || '—'}</span>
        </div>
      </div>
    </div>

    <div class="profile-section">
      <h3>Academic Performance</h3>
      <div class="profile-info-grid" style="grid-template-columns: repeat(4, 1fr);">
        <div class="profile-field" style="text-align:center;">
          <span class="field-label">SGPA</span>
          <span class="field-value sgpa-value ${student.sgpa != null ? sgpaColorClass(student.sgpa) : ''}" style="font-size:1.5rem;">${student.sgpa != null ? student.sgpa.toFixed(2) : '—'}</span>
        </div>
        <div class="profile-field" style="text-align:center;">
          <span class="field-label">Result</span>
          <span class="field-value"><span class="status-badge ${student.result === 'PASS' ? 'pass' : 'fail'}">${student.result}</span></span>
        </div>
        <div class="profile-field" style="text-align:center;">
          <span class="field-label">Overall Rank</span>
          <span class="field-value" style="color:var(--accent-cyan);">${student.rank != null ? ordinal(student.rank) + ' / ' + STUDENTS.filter(s => s.sgpa != null).length : '—'}</span>
        </div>
        <div class="profile-field" style="text-align:center;">
          <span class="field-label">Branch Rank</span>
          <span class="field-value" style="color:var(--accent-amber);">${student.branchRank != null ? ordinal(student.branchRank) + ' / ' + student.branchTotal : '—'}</span>
        </div>
      </div>
    </div>

    <div class="profile-section">
      <h3>Credit Summary</h3>
      <div class="profile-info-grid" style="grid-template-columns: repeat(3, 1fr);">
        <div class="profile-field" style="text-align:center;">
          <span class="field-label">Total Credits</span>
          <span class="field-value">${totalCredits}</span>
        </div>
        <div class="profile-field" style="text-align:center;">
          <span class="field-label">Earned Credits</span>
          <span class="field-value" style="color:var(--accent-emerald);">${earnedCredits}</span>
        </div>
        <div class="profile-field" style="text-align:center;">
          <span class="field-label">Subjects</span>
          <span class="field-value">${subjects.length}</span>
        </div>
      </div>
    </div>

    <div class="profile-section">
      <h3>Grade Distribution</h3>
      <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1rem;">
        ${Object.entries(gradeCounts).map(([g, c]) => `
          <span class="grade-badge ${gradeBadgeClass(g)}" style="font-size:0.8rem; padding:0.3rem 0.75rem;">
            ${g}: ${c}
          </span>
        `).join('')}
      </div>
    </div>

    <div class="profile-section">
      <h3>Subject-wise Results</h3>
      <div class="data-table-wrap">
        <table class="profile-subjects-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Course Code</th>
              <th>Type</th>
              <th>Total Credit</th>
              <th>Earned Credit</th>
              <th>Grade</th>
            </tr>
          </thead>
          <tbody>
            ${subjects.map((s, i) => {
              const code = s.code || '';
              const type = code.includes('[T]') ? 'Theory' : code.includes('[P]') ? 'Practical' : '—';
              const cleanCode = code.replace(/- \[.\]/g, '').replace(/\[.\]/g, '').trim();
              return `
                <tr>
                  <td style="color:var(--text-muted);">${i + 1}</td>
                  <td style="font-family:var(--font-mono); font-size:0.8rem;">${cleanCode}</td>
                  <td><span style="font-size:0.7rem; padding:0.1rem 0.4rem; border-radius:4px; background:${type === 'Theory' ? 'rgba(102,126,234,0.1)' : 'rgba(16,185,129,0.1)'}; color:${type === 'Theory' ? 'var(--accent-blue)' : 'var(--accent-emerald)'};">${type}</span></td>
                  <td style="text-align:center;">${s.tc || '—'}</td>
                  <td style="text-align:center;">${s.ec || '—'}</td>
                  <td><span class="grade-badge ${gradeBadgeClass(s.grade)}">${s.grade || '—'}</span></td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;

  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeProfile() {
  document.getElementById('profileModal').classList.remove('active');
  document.body.style.overflow = '';
}

// Close on backdrop click
document.getElementById('profileModal')?.addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeProfile();
});

// Close on Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeProfile();
});
