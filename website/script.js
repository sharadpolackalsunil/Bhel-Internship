/* ============================================================
   BHEL Portfolio — Shared JavaScript
   Navigation, scroll animations, gallery, counters, charts
   ============================================================ */

// ── Navbar Scroll Effect ──
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 50);
  });
}

// ── Mobile Toggle ──
const mobileToggle = document.getElementById('mobileToggle');
const navLinks = document.getElementById('navLinks');
if (mobileToggle && navLinks) {
  mobileToggle.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    mobileToggle.textContent = navLinks.classList.contains('open') ? '✕' : '☰';
  });
}

// ── Intersection Observer (Scroll Animations) ──
const observerOptions = { threshold: 0.1, rootMargin: '0px 0px -50px 0px' };
const scrollObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      // Trigger counters
      if (entry.target.closest('.hero-stats') || entry.target.querySelector('[data-count]')) {
        startCounters(entry.target);
      }
      // Trigger bar animations
      entry.target.querySelectorAll('.bar-fill').forEach(bar => {
        const w = bar.getAttribute('data-width');
        if (w) bar.style.width = w;
      });
    }
  });
}, observerOptions);

document.querySelectorAll('.animate-on-scroll, .pipeline-step').forEach(el => {
  scrollObserver.observe(el);
});

// ── Counter Animation ──
function startCounters(container) {
  const counters = container.querySelectorAll ? container.querySelectorAll('[data-count]') : document.querySelectorAll('[data-count]');
  counters.forEach(counter => {
    if (counter.dataset.counted) return;
    counter.dataset.counted = 'true';
    const target = parseInt(counter.dataset.count);
    const suffix = counter.dataset.suffix || '';
    const duration = 2000;
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      counter.textContent = Math.round(eased * target) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });
}

// Auto-start hero counters
const heroStats = document.querySelector('.hero-stats');
if (heroStats) {
  const heroObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      startCounters(heroStats);
      heroObserver.disconnect();
    }
  }, { threshold: 0.5 });
  heroObserver.observe(heroStats);
}

// ── Pipeline Animation ──
const pipelineSteps = document.querySelectorAll('.pipeline-step');
if (pipelineSteps.length) {
  const pipelineObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      pipelineSteps.forEach((step, i) => {
        setTimeout(() => step.classList.add('visible'), i * 150);
      });
      pipelineObserver.disconnect();
    }
  }, { threshold: 0.3 });
  pipelineObserver.observe(document.getElementById('pipelineFlow') || pipelineSteps[0]);
}

// ── Challenge Accordion ──
function toggleChallenge(btn) {
  const item = btn.closest('.challenge-item');
  const body = item.querySelector('.challenge-body');
  const inner = item.querySelector('.challenge-body-inner');
  const isOpen = item.classList.contains('open');

  // Close all others
  document.querySelectorAll('.challenge-item.open').forEach(other => {
    if (other !== item) {
      other.classList.remove('open');
      other.querySelector('.challenge-body').style.maxHeight = '0';
    }
  });

  if (isOpen) {
    item.classList.remove('open');
    body.style.maxHeight = '0';
  } else {
    item.classList.add('open');
    body.style.maxHeight = inner.scrollHeight + 'px';
  }
}

// ── Gallery ──
const galleryTrack = document.getElementById('galleryTrack');
const galleryDots = document.getElementById('galleryDots');
const galleryPrev = document.getElementById('galleryPrev');
const galleryNext = document.getElementById('galleryNext');

if (galleryTrack) {
  const slides = galleryTrack.querySelectorAll('.gallery-slide');
  let currentSlide = 0;

  // Create dots
  slides.forEach((_, i) => {
    const dot = document.createElement('div');
    dot.className = 'gallery-dot' + (i === 0 ? ' active' : '');
    dot.addEventListener('click', () => goToSlide(i));
    galleryDots.appendChild(dot);
  });

  function goToSlide(n) {
    currentSlide = ((n % slides.length) + slides.length) % slides.length;
    galleryTrack.style.transform = `translateX(-${currentSlide * 100}%)`;
    galleryDots.querySelectorAll('.gallery-dot').forEach((d, i) => {
      d.classList.toggle('active', i === currentSlide);
    });
  }

  galleryPrev.addEventListener('click', () => goToSlide(currentSlide - 1));
  galleryNext.addEventListener('click', () => goToSlide(currentSlide + 1));

  // Auto-advance
  let autoPlay = setInterval(() => goToSlide(currentSlide + 1), 5000);
  const gallery = document.getElementById('gallery');
  gallery.addEventListener('mouseenter', () => clearInterval(autoPlay));
  gallery.addEventListener('mouseleave', () => {
    autoPlay = setInterval(() => goToSlide(currentSlide + 1), 5000);
  });
}

// ── Academic Trend Chart ──
const trendCanvas = document.getElementById('trendChart');
if (trendCanvas) {
  const ctx = trendCanvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;

  function drawTrendChart() {
    const rect = trendCanvas.parentElement.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    trendCanvas.width = w * dpr;
    trendCanvas.height = h * dpr;
    trendCanvas.style.width = w + 'px';
    trendCanvas.style.height = h + 'px';
    ctx.scale(dpr, dpr);

    const padding = { top: 30, right: 30, bottom: 40, left: 50 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    // Data
    const semesters = ['Sem 2', 'Sem 3', 'Sem 4'];
    const cgpa = [7.55, 7.61, 7.77];
    const sgpa = [7.55, 7.73, 8.22];
    const minVal = 5;
    const maxVal = 10;

    function xPos(i) { return padding.left + (i / (semesters.length - 1)) * chartW; }
    function yPos(v) { return padding.top + chartH - ((v - minVal) / (maxVal - minVal)) * chartH; }

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let v = minVal; v <= maxVal; v += 0.5) {
      const y = yPos(v);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();
    }

    // Y-axis labels
    ctx.fillStyle = '#64748b';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'right';
    for (let v = minVal + 0.5; v <= maxVal; v += 0.5) {
      ctx.fillText(v.toFixed(1), padding.left - 8, yPos(v) + 4);
    }

    // X-axis labels
    ctx.textAlign = 'center';
    semesters.forEach((label, i) => {
      ctx.fillText(label, xPos(i), h - padding.bottom + 25);
    });

    // Draw CGPA line
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    cgpa.forEach((v, i) => {
      i === 0 ? ctx.moveTo(xPos(i), yPos(v)) : ctx.lineTo(xPos(i), yPos(v));
    });
    ctx.stroke();

    // CGPA dots
    cgpa.forEach((v, i) => {
      ctx.fillStyle = '#0a0e1a';
      ctx.beginPath();
      ctx.arc(xPos(i), yPos(v), 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#667eea';
      ctx.lineWidth = 2.5;
      ctx.stroke();
    });

    // Draw SGPA line (dashed)
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    sgpa.forEach((v, i) => {
      i === 0 ? ctx.moveTo(xPos(i), yPos(v)) : ctx.lineTo(xPos(i), yPos(v));
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // SGPA dots
    sgpa.forEach((v, i) => {
      ctx.fillStyle = '#0a0e1a';
      ctx.beginPath();
      ctx.arc(xPos(i), yPos(v), 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }

  // Observe and draw
  const trendObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      drawTrendChart();
      trendObserver.disconnect();
    }
  }, { threshold: 0.3 });
  trendObserver.observe(trendCanvas.parentElement);
  window.addEventListener('resize', () => {
    if (trendCanvas.parentElement.getBoundingClientRect().width > 0) drawTrendChart();
  });
}

// ── Smooth Scroll for anchor links ──
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', (e) => {
    const target = document.querySelector(link.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (navLinks) navLinks.classList.remove('open');
    }
  });
});

// ── Utility: Get SGPA color class ──
function sgpaColorClass(sgpa) {
  if (sgpa >= 9.0) return 'high';
  if (sgpa >= 7.0) return 'mid';
  return 'low';
}

// ── Utility: Get grade badge class ──
function gradeBadgeClass(grade) {
  const g = (grade || '').toUpperCase();
  if (g === 'AAA') return 'grade-aaa';
  if (g === 'AA') return 'grade-aa';
  if (g === 'A' || g === 'A+') return 'grade-a';
  if (g.startsWith('B')) return 'grade-b';
  if (g.startsWith('C') || g.startsWith('D') || g === 'F') return 'grade-c';
  return 'grade-other';
}

// ── Utility: Ordinal suffix ──
function ordinal(n) {
  const s = ['th','st','nd','rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}
