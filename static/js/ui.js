/**
 * static/js/ui.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Shared UI utilities: toasts, loaders, form validation, skeleton rendering.
 * ─────────────────────────────────────────────────────────────────────────────
 */

const UI = {

  // ── Toast Notifications ──────────────────────────────────────────────────
  /**
   * Show a toast notification.
   * @param {string}  message
   * @param {'success'|'error'|'warning'|'info'} type
   * @param {string}  title    — optional heading
   * @param {number}  duration — ms before auto-dismiss (0 = manual)
   */
  showToast(message, type = 'info', title = '', duration = 4500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
      success: 'bi-check-circle-fill',
      error:   'bi-x-circle-fill',
      warning: 'bi-exclamation-triangle-fill',
      info:    'bi-info-circle-fill',
    };
    const defaultTitles = {
      success: 'Success',
      error:   'Error',
      warning: 'Warning',
      info:    'Info',
    };

    const toastEl = document.createElement('div');
    toastEl.className = `toast-item toast-${type}`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.innerHTML = `
      <i class="bi ${icons[type] || icons.info} toast-icon"></i>
      <div class="toast-content">
        <div class="toast-title">${title || defaultTitles[type]}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" aria-label="Close toast">
        <i class="bi bi-x-lg"></i>
      </button>
    `;

    const closeBtn = toastEl.querySelector('.toast-close');
    const dismiss  = () => {
      toastEl.style.animation = 'toastSlideOut .25s ease forwards';
      setTimeout(() => toastEl.remove(), 260);
    };
    closeBtn.addEventListener('click', dismiss);

    container.appendChild(toastEl);
    if (duration > 0) setTimeout(dismiss, duration);
  },

  // ── Global Loader ─────────────────────────────────────────────────────────
  showLoader() {
    const el = document.getElementById('globalLoader');
    if (el) el.classList.remove('d-none');
  },

  hideLoader() {
    const el = document.getElementById('globalLoader');
    if (el) el.classList.add('d-none');
  },

  // ── Button Loading State ──────────────────────────────────────────────────
  setButtonLoading(btn, loading = true, label = 'Loading…') {
    if (!btn) return;
    if (loading) {
      btn.dataset.originalText = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>${label}`;
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.originalText || 'Submit';
    }
  },

  // ── Form Validation ───────────────────────────────────────────────────────
  /**
   * Validate a form element.
   * Returns true if valid; marks invalid fields and shows messages.
   */
  validateForm(formEl) {
    if (!formEl) return false;
    let valid = true;

    formEl.querySelectorAll('[required]').forEach(input => {
      const val = input.value.trim();
      if (!val) {
        this.setFieldError(input, 'This field is required.');
        valid = false;
      } else {
        this.clearFieldError(input);
      }

      // Extra: email pattern
      if (input.type === 'email' && val) {
        const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRe.test(val)) {
          this.setFieldError(input, 'Enter a valid email address.');
          valid = false;
        }
      }

      // Extra: password minimum length
      if (input.type === 'password' && val && val.length < 8) {
        this.setFieldError(input, 'Password must be at least 8 characters.');
        valid = false;
      }

      // Extra: confirm password match
      if (input.dataset.match) {
        const matchEl = formEl.querySelector(`[name="${input.dataset.match}"]`);
        if (matchEl && val !== matchEl.value) {
          this.setFieldError(input, 'Passwords do not match.');
          valid = false;
        }
      }
    });

    return valid;
  },

  setFieldError(input, message) {
    input.classList.add('is-invalid');
    let fb = input.nextElementSibling;
    if (!fb || !fb.classList.contains('invalid-feedback')) {
      fb = document.createElement('div');
      fb.className = 'invalid-feedback';
      input.parentNode.insertBefore(fb, input.nextSibling);
    }
    fb.textContent = message;
  },

  clearFieldError(input) {
    input.classList.remove('is-invalid');
    const fb = input.nextElementSibling;
    if (fb && fb.classList.contains('invalid-feedback')) fb.textContent = '';
  },

  clearAllErrors(formEl) {
    if (!formEl) return;
    formEl.querySelectorAll('.is-invalid').forEach(el => this.clearFieldError(el));
  },

  // ── Skeleton Cards ────────────────────────────────────────────────────────
  skeletonCard(count = 3) {
    return Array.from({ length: count }, () => `
      <div class="col">
        <div class="medicine-card p-3">
          <div class="skeleton mb-3" style="height:56px;border-radius:8px;"></div>
          <div class="skeleton mb-2" style="height:18px;width:70%;"></div>
          <div class="skeleton mb-2" style="height:14px;width:50%;"></div>
          <div class="skeleton"      style="height:14px;width:80%;"></div>
        </div>
      </div>
    `).join('');
  },

  // ── Render helpers ────────────────────────────────────────────────────────
  renderEmpty(container, message = 'No results found.', icon = 'bi-search') {
    if (!container) return;
    container.innerHTML = `
      <div class="col-12 text-center py-5">
        <i class="bi ${icon} text-muted" style="font-size:3rem;opacity:.4;"></i>
        <p class="text-muted mt-3 mb-0">${message}</p>
      </div>
    `;
  },

  renderError(container, message = 'Failed to load data.') {
    if (!container) return;
    container.innerHTML = `
      <div class="col-12">
        <div class="alert alert-danger d-flex align-items-center gap-2">
          <i class="bi bi-exclamation-circle-fill"></i>
          <span>${message}</span>
        </div>
      </div>
    `;
  },

  // ── Pagination ────────────────────────────────────────────────────────────
  renderPagination(container, paginationData, onPageChange) {
    if (!container || !paginationData) return;
    const { page, pages, total } = paginationData;
    if (pages <= 1) { container.innerHTML = ''; return; }

    const createPageBtn = (p, label, disabled = false, active = false) => {
      const li = document.createElement('li');
      li.className = `page-item${disabled ? ' disabled' : ''}${active ? ' active' : ''}`;
      li.innerHTML = `<button class="page-link">${label}</button>`;
      if (!disabled && !active) {
        li.querySelector('button').addEventListener('click', () => onPageChange(p));
      }
      return li;
    };

    const ul = document.createElement('ul');
    ul.className = 'pagination pagination-sm justify-content-center mb-0';
    ul.appendChild(createPageBtn(page - 1, '&laquo;', page <= 1));
    for (let i = Math.max(1, page - 2); i <= Math.min(pages, page + 2); i++) {
      ul.appendChild(createPageBtn(i, i, false, i === page));
    }
    ul.appendChild(createPageBtn(page + 1, '&raquo;', page >= pages));

    container.innerHTML = '';
    container.appendChild(ul);
  },

  // ── Format helpers ────────────────────────────────────────────────────────
  formatDistance(km) {
    if (km < 1) return `${Math.round(km * 1000)} m`;
    return `${km.toFixed(1)} km`;
  },

  formatDate(isoStr) {
    if (!isoStr) return '—';
    return new Date(isoStr).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  },

  formatCurrency(amount) {
    return `₹${parseFloat(amount || 0).toFixed(2)}`;
  },

  timeAgo(isoStr) {
    const diff = Date.now() - new Date(isoStr).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1)  return 'just now';
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24)   return `${hours} hr ago`;
    const days = Math.floor(hours / 24);
    return `${days} day${days > 1 ? 's' : ''} ago`;
  },
};

// Inject slide-out animation if not present
const styleTag = document.createElement('style');
styleTag.textContent = `@keyframes toastSlideOut{to{opacity:0;transform:translateX(110%)}}`;
document.head.appendChild(styleTag);

window.UI = UI;
