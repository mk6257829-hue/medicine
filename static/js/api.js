/**
 * static/js/api.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Centralised Fetch API wrapper for all backend calls.
 * Handles JWT tokens, CSRF, standardised errors, and JSON serialisation.
 * ─────────────────────────────────────────────────────────────────────────────
 */

const API_BASE = '/api';

/** Low-level request helper — use the named methods below instead. */
async function apiRequest(endpoint, options = {}) {
  const {
    method    = 'GET',
    body      = null,
    isForm    = false,   // set true for FormData uploads
    silent    = false,   // suppress error toasts when true
    raw       = false,   // return raw Response when true
  } = options;

  const headers = {};

  // Attach JSON content-type only for non-form requests
  if (body && !isForm) {
    headers['Content-Type'] = 'application/json';
  }

  // Attach stored access token (if any)
  const token = Auth.getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const fetchOptions = {
    method,
    headers,
    credentials: 'include',   // send cookies (JWT cookie + CSRF)
  };

  if (body) {
    fetchOptions.body = isForm ? body : JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${endpoint}`, fetchOptions);
  } catch (networkErr) {
    if (!silent) UI.showToast('Network error — please check your connection.', 'error');
    throw networkErr;
  }

  if (raw) return response;

  let data;
  try {
    data = await response.json();
  } catch {
    data = { success: false, message: 'Invalid server response.', error: 'PARSE_ERROR' };
  }

  if (!response.ok && !silent) {
    const msg = data.message || 'An unexpected error occurred.';
    UI.showToast(msg, 'error');
  }

  // Auto-redirect on 401 (expired / missing token)
  if (response.status === 401 && !endpoint.startsWith('/auth/')) {
    Auth.clearSession();
    window.location.href = '/login?expired=1';
  }

  return { ok: response.ok, status: response.status, data };
}

// ── Convenience methods ──────────────────────────────────────────────────────
const API = {
  get:    (url, opts = {}) => apiRequest(url, { ...opts, method: 'GET' }),
  post:   (url, body, opts = {}) => apiRequest(url, { ...opts, method: 'POST',  body }),
  put:    (url, body, opts = {}) => apiRequest(url, { ...opts, method: 'PUT',   body }),
  patch:  (url, body, opts = {}) => apiRequest(url, { ...opts, method: 'PATCH', body }),
  delete: (url, opts = {}) => apiRequest(url, { ...opts, method: 'DELETE' }),
  upload: (url, formData, opts = {}) => apiRequest(url, { ...opts, method: 'POST', body: formData, isForm: true }),

  // ── Named endpoints ────────────────────────────────────────────────────────

  // Auth
  register: (data)         => API.post('/auth/register', data),
  login:    (data)         => API.post('/auth/login', data),
  logout:   ()             => API.post('/auth/logout'),
  me:       ()             => API.get('/auth/me'),

  // Medicines
  getMedicines:  (params = '') => API.get(`/medicines/?${params}`),
  getMedicine:   (id)          => API.get(`/medicines/${id}`),
  searchMeds:    (q, params='')=> API.get(`/search/medicines?q=${encodeURIComponent(q)}&${params}`),
  getAvailability: (medId)     => API.get(`/search/availability/${medId}`),

  // Pharmacies
  getPharmacies:  (params = '') => API.get(`/pharmacies/?${params}`),
  getPharmacy:    (id)          => API.get(`/pharmacies/${id}`),
  getNearby:      (lat, lng, radius = 5) =>
    API.get(`/pharmacies/nearby?lat=${lat}&lng=${lng}&radius=${radius}`),

  // Inventory
  getInventory:    (params = '') => API.get(`/inventory/?${params}`),
  addInventory:    (data)        => API.post('/inventory/', data),
  updateInventory: (id, data)    => API.put(`/inventory/${id}`, data),
  deleteInventory: (id)          => API.delete(`/inventory/${id}`),

  // Orders
  getOrders:    (params = '') => API.get(`/orders/?${params}`),
  getOrder:     (id)          => API.get(`/orders/${id}`),
  createOrder:  (data)        => API.post('/orders/', data),
  updateOrderStatus: (id, status) => API.put(`/orders/${id}/status`, { status }),

  // Prescriptions
  uploadPrescription: (formData)    => API.upload('/prescriptions/', formData),
  getPrescriptions:   (params = '') => API.get(`/prescriptions/?${params}`),
  updatePrescriptionStatus: (id, status, note = '') =>
    API.put(`/prescriptions/${id}/status`, { status, note }),

  // Admin
  adminDashboard:      ()             => API.get('/admin/dashboard'),
  adminUsers:          (params = '')  => API.get(`/admin/users?${params}`),
  adminPharmacies:     (params = '')  => API.get(`/admin/pharmacies?${params}`),
  adminVerifyPharmacy: (id, status)   => API.put(`/admin/pharmacies/${id}/verify`, { status }),
  adminMedicines:      (params = '')  => API.get(`/admin/medicines?${params}`),
  createMedicine:      (data)         => API.post('/medicines/', data),
  updateMedicine:      (id, data)     => API.put(`/medicines/${id}`, data),
};

window.API = API;
window.apiRequest = apiRequest;
