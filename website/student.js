/* ============================================================
   Student Portal — Logic
   Login validation, dashboard rendering, grade charts
   ============================================================ */

let currentStudent = null;

function handleStudentLogin(e) {
  e.preventDefault();
  const enrollment = document.getElementById('enrollmentInput').value.trim().toUpperCase();
  const errorEl = document.getElementById('loginError');

  // Find student in data
  const student = STUDENTS.find(s => s.enrollment === enrollment);

  if (!student) {
    errorEl.classList.add('show');
    errorEl.textContent = 'Student not found. Please check your enrollment number.';
    return false;
  }

  // Student found — store and show dashboard
  currentStudent = student;
  errorEl.classList.remove('show');
  
  document.getElementById('loginSection').style.display = 'none';
  document.getElementById('studentDashboard').classList.add('active');
  
  renderStudentDashboard(student);
  return false;
}

function studentLogout() {
  currentStudent = null;
  document.getElementById('studentDashboard').classList.remove('active');
  document.getElementById('loginSection').style.display = '';
  document.getElementById('enrollmentInput').value = '';
  document.getElementById('passwordInput').value = '';
}

function renderStudentDashboard(student) {
  // Avatar initials
  const initials = (student.name || '').split(' ').map(w => w[0]).join('').slice(0, 2);
  document.getElementById('studentAvatar').textContent = initials || '?';
  
  // Profile info
  document.getElementById('studentName').textContent = student.name || '—';
  document.getElementById('studentEnroll').textContent = student.enrollment;
  document.getElementById('studentBranch').textContent = student.branch;
  document.getElementById('studentSem').textContent = student.semester || '4';
  
  // Status badge
  const statusContainer = document.getElementById('studentStatusBadge');
  const status = (student.result || '').toUpperCase();
  if (status === 'PASS') {
    statusContainer.innerHTML = '<span class="pass-badge pass">✓ PASS</span>';
  } else if (status === 'FAIL') {
    statusContainer.innerHTML = '<span class="pass-badge fail">✗ FAIL</span>';
  } else {
    statusContainer.innerHTML = `<span class="pass-badge" style="background:rgba(100,116,139,0.15);color:var(--text-muted);">${status}</span>`;
  }

  // SGPA / CGPA
  const sgpa = student.sgpa;
  const cgpa = student.cgpa;
  document.getElementById('studentSGPA').textContent = sgpa != null ? sgpa.toFixed(2) : '—';
  document.getElementById('studentCGPA').textContent = cgpa != null ? cgpa.toFixed(2) : '—';
  
  // Rankings
  document.getElementById('studentRank').textContent = student.rank != null ? ordinal(student.rank) : '—';
  document.getElementById('studentBranchRank').textContent = student.branchRank != null 
    ? `${ordinal(student.branchRank)} / ${student.branchTotal}` 
    : '—';

  // Subjects table
  renderSubjectsTable(student.subjects || []);

  // Grade distribution chart
  renderGradeChart(student.subjects || []);
}

function renderSubjectsTable(subjects) {
  const tbody = document.getElementById('studentSubjectsBody');
  tbody.innerHTML = '';

  subjects.forEach((subj, i) => {
    const code = subj.code || '';
    // Determine type from code
    let type = '—';
    if (code.includes('[T]')) type = 'Theory';
    else if (code.includes('[P]')) type = 'Practical';

    const cleanCode = code.replace('- [T]', '').replace('- [P]', '').replace('[T]', '').replace('[P]', '').trim();
    const gradeClass = gradeBadgeClass(subj.grade);

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="color:var(--text-muted);">${i + 1}</td>
      <td style="font-family:var(--font-mono); font-size:0.8rem;">${cleanCode}</td>
      <td><span style="font-size:0.75rem; padding:0.15rem 0.5rem; border-radius:4px; background:${type === 'Theory' ? 'rgba(102,126,234,0.1)' : 'rgba(16,185,129,0.1)'}; color:${type === 'Theory' ? 'var(--accent-blue)' : 'var(--accent-emerald)'};">${type}</span></td>
      <td style="text-align:center;">${subj.tc || '—'}</td>
      <td style="text-align:center;">${subj.ec || '—'}</td>
      <td><span class="grade-badge ${gradeClass}">${subj.grade || '—'}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderGradeChart(subjects) {
  const container = document.getElementById('studentGradeChart');
  container.innerHTML = '';

  // Count grades
  const gradeCounts = {};
  subjects.forEach(s => {
    const g = (s.grade || 'Other').toUpperCase();
    gradeCounts[g] = (gradeCounts[g] || 0) + 1;
  });

  const gradeOrder = ['AAA', 'AA', 'A', 'B+', 'B', 'C', 'PS', 'F'];
  const sortedGrades = Object.keys(gradeCounts).sort((a, b) => {
    const ai = gradeOrder.indexOf(a);
    const bi = gradeOrder.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  const maxCount = Math.max(...Object.values(gradeCounts), 1);

  const gradeColors = {
    'AAA': '#10b981', 'AA': '#06b6d4', 'A': '#667eea', 'A+': '#667eea',
    'B+': '#f59e0b', 'B': '#f97316', 'C': '#f43f5e', 'D': '#ef4444',
    'F': '#dc2626', 'PS': '#94a3b8'
  };

  sortedGrades.forEach(grade => {
    const count = gradeCounts[grade];
    const heightPct = (count / maxCount) * 100;
    const color = gradeColors[grade] || '#64748b';

    const wrap = document.createElement('div');
    wrap.style.cssText = 'flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end;';
    
    wrap.innerHTML = `
      <div style="font-size:0.7rem; font-weight:700; color:${color}; margin-bottom:0.25rem;">${count}</div>
      <div style="width:100%; height:${heightPct}%; background:${color}; border-radius:4px 4px 0 0; min-height:4px; opacity:0.8; transition: height 0.8s ease;"></div>
      <div style="font-size:0.65rem; color:var(--text-muted); margin-top:0.5rem; font-weight:600;">${grade}</div>
    `;
    container.appendChild(wrap);
  });
}
