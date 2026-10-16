/**
 * static/js/auth.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Client-side session / JWT management.
 * Works with httpOnly cookie tokens (primary) + localStorage fallback.
 * ─────────────────────────────────────────────────────────────────────────────
 */

const Auth = {
  _tokenKey: 'mf_access_token',
  _userKey:  'mf_user',

  /** Store access token returned by /api/auth/login */
  setToken(token) {
    localStorage.setItem(this._tokenKey, token);
  },

  getToken() {
    return localStorage.getItem(this._tokenKey);
  },

  /** Cache basic user info in localStorage for UI purposes. */
  setUser(user) {
    localStorage.setItem(this._userKey, JSON.stringify(user));
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem(this._userKey));
    } catch {
      return null;
    }
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  getRole() {
    const user = this.getUser();
    return user ? user.role : null;
  },

  clearSession() {
    localStorage.removeItem(this._tokenKey);
    localStorage.removeItem(this._userKey);
  },

  /** Log the current user out — calls the backend then clears local state. */
  async logout() {
    try {
      await API.logout();
    } catch (_) { /* ignore network errors on logout */ }
    this.clearSession();
    window.location.href = '/login';
  },

  /**
   * After login, update the navbar to show user info.
   * Called from main.js on page load and after successful login.
   */
  updateNavbar() {
    const user = this.getUser();
    const navLoginBtn    = document.getElementById('navLoginBtn');
    const navRegisterBtn = document.getElementById('navRegisterBtn');
    const navUserMenu    = document.getElementById('navUserMenu');
    const navUserName    = document.getElementById('navUserName');
    const navAvatarInit  = document.getElementById('navAvatarInitial');

    if (!user || !this.isLoggedIn()) {
      // Show guest buttons
      if (navLoginBtn)    navLoginBtn.classList.remove('d-none');
      if (navRegisterBtn) navRegisterBtn.classList.remove('d-none');
      if (navUserMenu)    navUserMenu.classList.add('d-none');
      return;
    }

    // Show user menu
    if (navLoginBtn)    navLoginBtn.classList.add('d-none');
    if (navRegisterBtn) navRegisterBtn.classList.add('d-none');
    if (navUserMenu)    navUserMenu.classList.remove('d-none');
    if (navUserName)    navUserName.textContent = user.name?.split(' ')[0] || 'User';
    if (navAvatarInit)  navAvatarInit.textContent = (user.name?.[0] || 'U').toUpperCase();

    // Update dropdown links based on role
    const role = user.role;
    if (role === 'PHARMACY_OWNER' || role === 'PHARMACIST') {
      const dashLink = navUserMenu.querySelector('a[href="/dashboard"]');
      if (dashLink) dashLink.href = '/pharmacy/dashboard';
    } else if (role === 'ADMIN') {
      const dashLink = navUserMenu.querySelector('a[href="/dashboard"]');
      if (dashLink) dashLink.href = '/admin/dashboard';
    }
  },

  /** Redirect user to role-appropriate dashboard. */
  redirectToDashboard() {
    const role = this.getRole();
    const routes = {
      ADMIN:          '/admin/dashboard',
      PHARMACY_OWNER: '/pharmacy/dashboard',
      PHARMACIST:     '/pharmacy/dashboard',
      USER:           '/dashboard',
    };
    window.location.href = routes[role] || '/dashboard';
  },
};

window.Auth = Auth;
