// ===== STATE =====
let selectedStars = 4;
let deleteId = null;

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
  setupNav();
  setupStarButtons();
  loadStats();
  loadDashTable();
  loadHotelsTable();

  document.getElementById('add-btn').addEventListener('click', () => {
    resetForm();
    showPage('add');
  });

  document.getElementById('logout-btn').addEventListener('click', async () => {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login';
  });
});

// ===== 401 HANDLER =====
async function apiFetch(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401) { window.location.href = '/login'; return null; }
  return res;
}

// ===== NAVIGATION =====
function setupNav() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => showPage(item.dataset.page));
  });
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  const nav = document.querySelector(`.nav-item[data-page="${name}"]`);
  if (nav) nav.classList.add('active');
  const titles = {
    dashboard: 'Dashboard',
    hotels: 'Mehmonxonalar',
    add: 'Yangi qo\'shish',
    bookings: 'Bronlar boshqaruvi',
    search: 'Qidirish'
  };
  document.getElementById('page-title').textContent = titles[name] || name;
  if (name === 'bookings') loadAllBookings();
}

// ===== STARS =====
function setupStarButtons() {
  document.querySelectorAll('.star-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedStars = parseInt(btn.dataset.v);
      document.querySelectorAll('.star-btn').forEach(b => {
        b.classList.toggle('on', parseInt(b.dataset.v) <= selectedStars);
      });
    });
  });
}

function setStars(n) {
  selectedStars = n;
  document.querySelectorAll('.star-btn').forEach(b => {
    b.classList.toggle('on', parseInt(b.dataset.v) <= n);
  });
}

// ===== STATS =====
async function loadStats() {
  const res = await apiFetch('/api/stats');
  if (!res) return;
  const d = await res.json();
  document.getElementById('stat-total').textContent = d.total;
  document.getElementById('stat-avg').textContent = '$' + Math.round(d.avg_price || 0);
  document.getElementById('stat-bookings').textContent = d.bookings_count ?? '—';
  document.getElementById('stat-clients').textContent = d.clients_count ?? '—';
}

// ===== DASHBOARD TABLE =====
async function loadDashTable() {
  const res = await apiFetch('/api/hotels');
  if (!res) return;
  const hotels = await res.json();
  document.getElementById('dash-count').textContent = hotels.length + ' ta';
  const tbody = document.getElementById('dash-tbody');
  tbody.innerHTML = hotels.map(h => `
    <tr>
      <td><strong>${esc(h.name)}</strong></td>
      <td>${esc(h.region)}</td>
      <td><span class="badge badge-gold">$${h.price}</span></td>
      <td><span class="stars">${'★'.repeat(h.stars)}</span></td>
      <td>${icon(h.wifi)}</td>
      <td>${icon(h.breakfast)}</td>
      <td>${icon(h.parking)}</td>
    </tr>
  `).join('') || `<tr><td colspan="7" class="empty-msg"><i class="fa-solid fa-building"></i><br>Mehmonxona yo'q</td></tr>`;
}

// ===== HOTELS TABLE =====
async function loadHotelsTable() {
  const res = await apiFetch('/api/hotels');
  if (!res) return;
  const hotels = await res.json();
  const tbody = document.getElementById('hotels-tbody');
  tbody.innerHTML = hotels.length ? hotels.map(h => `
    <tr>
      <td style="color:#94a3b8">#${h.id}</td>
      <td><strong>${esc(h.name)}</strong></td>
      <td>${esc(h.region)}</td>
      <td><span class="badge badge-gold">$${h.price}</span></td>
      <td><span class="stars">${'★'.repeat(h.stars)}</span></td>
      <td>${amenityBadges(h)}</td>
      <td>
        <div class="action-btns">
          <button class="btn-action" onclick="editHotel(${JSON.stringify(h).replace(/"/g,'&quot;')})">
            <i class="fa-solid fa-pen"></i> Tahrir
          </button>
          <button class="btn-action del" onclick="confirmDelete(${h.id})">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </td>
    </tr>
  `).join('') : `<tr><td colspan="7" class="empty-msg"><i class="fa-solid fa-building"></i><br>Mehmonxona topilmadi</td></tr>`;
}

function amenityBadges(h) {
  let out = '';
  if (h.wifi) out += '<span class="badge badge-blue" style="margin-right:4px"><i class="fa-solid fa-wifi" style="font-size:10px"></i></span>';
  if (h.breakfast) out += '<span class="badge badge-green" style="margin-right:4px"><i class="fa-solid fa-mug-hot" style="font-size:10px"></i></span>';
  if (h.parking) out += '<span class="badge badge-gold"><i class="fa-solid fa-square-parking" style="font-size:10px"></i></span>';
  return out || '<span style="color:#cbd5e1">—</span>';
}

function icon(val) {
  return val
    ? '<i class="fa-solid fa-check icon-check"></i>'
    : '<i class="fa-solid fa-xmark icon-x"></i>';
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ===== SAVE / UPDATE =====
async function saveHotel() {
  const name = document.getElementById('f-name').value.trim();
  const region = document.getElementById('f-region').value.trim();
  const price = document.getElementById('f-price').value.trim();

  if (!name || !region || !price) {
    showToast('Barcha maydonlarni to\'ldiring!', 'error');
    return;
  }

  const data = {
    name, region, price,
    stars: selectedStars,
    wifi: document.getElementById('f-wifi').checked,
    breakfast: document.getElementById('f-breakfast').checked,
    parking: document.getElementById('f-parking').checked,
    description: document.getElementById('f-desc').value.trim(),
  };

  const editId = document.getElementById('edit-id').value;
  const url = editId ? `/api/hotels/${editId}` : '/api/hotels';
  const method = editId ? 'PUT' : 'POST';

  const res = await apiFetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res) return;
  const result = await res.json();

  if (result.success) {
    showToast(editId ? 'Yangilandi!' : 'Saqlandi!', 'success');
    resetForm();
    loadStats();
    loadDashTable();
    loadHotelsTable();
    showPage('hotels');
  }
}

// ===== EDIT =====
function editHotel(h) {
  document.getElementById('edit-id').value = h.id;
  document.getElementById('f-name').value = h.name;
  document.getElementById('f-region').value = h.region;
  document.getElementById('f-price').value = h.price;
  document.getElementById('f-wifi').checked = !!h.wifi;
  document.getElementById('f-breakfast').checked = !!h.breakfast;
  document.getElementById('f-parking').checked = !!h.parking;
  document.getElementById('f-desc').value = h.description || '';
  setStars(h.stars);
  document.getElementById('form-title').textContent = 'Mehmonxonani tahrirlash';
  showPage('add');
}

// ===== DELETE =====
function confirmDelete(id) {
  deleteId = id;
  document.getElementById('modal-overlay').classList.add('show');
  document.getElementById('confirm-delete').onclick = async () => {
    const res = await apiFetch(`/api/hotels/${deleteId}`, { method: 'DELETE' });
    if (!res) return;
    const result = await res.json();
    if (result.success) {
      showToast('O\'chirildi!', 'success');
      loadStats();
      loadDashTable();
      loadHotelsTable();
    }
    closeModal();
  };
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('show');
  deleteId = null;
}

// ===== SEARCH =====
async function searchHotels() {
  const region = document.getElementById('s-region').value.trim();
  const price = document.getElementById('s-price').value.trim();
  const stars = document.getElementById('s-stars').value;
  const params = new URLSearchParams();
  if (region) params.append('region', region);
  if (price) params.append('max_price', price);
  if (stars) params.append('stars', stars);

  const res = await apiFetch('/api/hotels?' + params.toString());
  if (!res) return;
  const hotels = await res.json();
  const tbody = document.getElementById('search-tbody');

  tbody.innerHTML = hotels.length ? hotels.map(h => `
    <tr>
      <td><strong>${esc(h.name)}</strong></td>
      <td>${esc(h.region)}</td>
      <td><span class="badge badge-gold">$${h.price}</span></td>
      <td><span class="stars">${'★'.repeat(h.stars)}</span></td>
      <td>${icon(h.wifi)}</td>
      <td>${icon(h.breakfast)}</td>
      <td>${icon(h.parking)}</td>
    </tr>
  `).join('') : `<tr><td colspan="7" class="empty-msg"><i class="fa-solid fa-magnifying-glass"></i><br>Natija topilmadi</td></tr>`;
}

// ===== ALL BOOKINGS (ADMIN) =====
async function loadAllBookings() {
  const res = await apiFetch('/api/bookings/all');
  if (!res) return;
  const bookings = await res.json();
  document.getElementById('all-bookings-count').textContent = bookings.length + ' ta';
  const tbody = document.getElementById('bookings-tbody');

  if (!bookings.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-msg"><i class="fa-solid fa-calendar"></i><br>Hali bronlar yo'q</td></tr>`;
    return;
  }

  const statusLabel = { pending: 'Kutilmoqda', confirmed: 'Tasdiqlangan', cancelled: 'Bekor' };

  tbody.innerHTML = bookings.map(b => `
    <tr>
      <td style="color:#94a3b8">#${b.id}</td>
      <td>
        <strong>${esc(b.full_name || b.username)}</strong>
        <div style="font-size:11px;color:#94a3b8">@${esc(b.username)}</div>
      </td>
      <td><strong>${esc(b.hotel_name)}</strong></td>
      <td>${esc(b.region)}</td>
      <td>${b.check_in}</td>
      <td>${b.check_out}</td>
      <td style="text-align:center">${b.guests}</td>
      <td><span class="badge badge-gold">$${b.total_price}</span></td>
      <td>
        <select class="status-select" onchange="updateBookingStatus(${b.id}, this.value)">
          <option value="pending"   ${b.status==='pending'   ?'selected':''}>⏳ Kutilmoqda</option>
          <option value="confirmed" ${b.status==='confirmed' ?'selected':''}>✅ Tasdiqlangan</option>
          <option value="cancelled" ${b.status==='cancelled' ?'selected':''}>❌ Bekor</option>
        </select>
      </td>
      <td>
        <button class="btn-action del" onclick="deleteBooking(${b.id})">
          <i class="fa-solid fa-trash"></i>
        </button>
      </td>
    </tr>
  `).join('');
}

async function updateBookingStatus(id, status) {
  const res = await apiFetch(`/api/bookings/${id}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status })
  });
  if (!res) return;
  const data = await res.json();
  if (data.success) showToast('Status yangilandi!', 'success');
  else showToast('Xatolik yuz berdi!', 'error');
}

async function deleteBooking(id) {
  if (!confirm('Bu bronni o\'chirishni xohlaysizmi?')) return;
  const res = await apiFetch(`/api/bookings/${id}`, { method: 'DELETE' });
  if (!res) return;
  const data = await res.json();
  if (data.success) {
    showToast('Bron o\'chirildi!', 'success');
    loadAllBookings();
    loadStats();
  }
}

// ===== HELPERS =====
function resetForm() {
  document.getElementById('edit-id').value = '';
  document.getElementById('f-name').value = '';
  document.getElementById('f-region').value = '';
  document.getElementById('f-price').value = '';
  document.getElementById('f-desc').value = '';
  document.getElementById('f-wifi').checked = false;
  document.getElementById('f-breakfast').checked = false;
  document.getElementById('f-parking').checked = false;
  setStars(4);
  document.getElementById('form-title').textContent = 'Yangi mehmonxona qo\'shish';
}

let toastTimer;
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (type ? ' ' + type : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2800);
}
