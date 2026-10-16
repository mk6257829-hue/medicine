/**
 * static/js/main.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Application bootstrap and shared page behaviour.
 * Runs on every page load.
 * ─────────────────────────────────────────────────────────────────────────────
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialise auth-aware navbar
  Auth.updateNavbar();

  // 2. Navbar scroll shadow
  const nav = document.getElementById('mainNav');
  if (nav) {
    const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 10);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // 3. Logout button
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => Auth.logout());
  }

  // 4. Highlight active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll('#navbarMain .nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // 5. Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // 6. Global search bar (hero / header)
  initGlobalSearch();

  // 7. Animate elements on scroll
  initScrollAnimations();

  // 8. Geolocation helper (if page requests it)
  if (window.initGeolocation) window.initGeolocation();
});

// ─── Global Search ────────────────────────────────────────────────────────────
function initGlobalSearch() {
  const searchInput = document.getElementById('heroSearchInput');
  const searchBtn   = document.getElementById('heroSearchBtn');
  const dropdown    = document.getElementById('searchDropdown');

  if (!searchInput) return;

  let debounceTimer;

  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = searchInput.value.trim();
    if (q.length < 2) { hideDropdown(); return; }
    debounceTimer = setTimeout(() => fetchSearchSuggestions(q), 300);
  });

  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') performSearch();
  });

  if (searchBtn) {
    searchBtn.addEventListener('click', performSearch);
  }

  // Close dropdown on outside click
  document.addEventListener('click', e => {
    if (!searchInput.closest('.search-bar-wrap')?.contains(e.target)) {
      hideDropdown();
    }
  });

  async function fetchSearchSuggestions(q) {
    if (!dropdown) return;
    dropdown.innerHTML = `<div class="autocomplete-item"><div class="skeleton" style="height:36px;width:100%;border-radius:6px;"></div></div>`;
    dropdown.classList.remove('d-none');

    const { ok, data } = await API.searchMeds(q, 'per_page=6');
    if (!ok || !data?.data?.items?.length) {
      dropdown.innerHTML = `<div class="autocomplete-item text-muted" style="justify-content:center;font-size:.875rem;">No results for "${q}"</div>`;
      return;
    }

    dropdown.innerHTML = data.data.items.map(med => `
      <div class="autocomplete-item" data-id="${med._id}" role="option" tabindex="0">
        <div class="autocomplete-item-icon"><i class="bi bi-capsule"></i></div>
        <div>
          <div class="autocomplete-item-name">${highlightMatch(med.name, q)}</div>
          <div class="autocomplete-item-sub">${med.generic_name || ''} · ${med.dosage_form || ''}</div>
        </div>
      </div>
    `).join('');

    dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = item.dataset.id;
        if (id) window.location.href = `/medicine/${id}`;
      });
    });
  }

  function performSearch() {
    const q = searchInput.value.trim();
    if (!q) { UI.showToast('Please enter a medicine name to search.', 'warning'); return; }
    window.location.href = `/medicines?q=${encodeURIComponent(q)}`;
  }

  function hideDropdown() {
    if (dropdown) dropdown.classList.add('d-none');
  }

  function highlightMatch(text, query) {
    if (!query) return text;
    const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(re, '<mark>$1</mark>');
  }
}

// ─── Scroll Animations ─────────────────────────────────────────────────────────
function initScrollAnimations() {
  const els = document.querySelectorAll('[data-animate]');
  if (!els.length) return;

  const observer = new IntersectionObserver(
    entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animated');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
  );

  els.forEach(el => observer.observe(el));
}

// ─── Nearby pharmacy search (geolocation) ────────────────────────────────────
window.getUserLocation = function () {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      err => reject(err),
      { timeout: 8000, maximumAge: 60000 }
    );
  });
};

// ─── Counter animation for stats ─────────────────────────────────────────────
window.animateCounters = function () {
  document.querySelectorAll('[data-counter]').forEach(el => {
    const target = parseInt(el.dataset.counter, 10);
    const duration = 1500;
    const step = Math.ceil(target / (duration / 16));
    let current = 0;
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current.toLocaleString('en-IN');
      if (current >= target) clearInterval(timer);
    }, 16);
  });
};
