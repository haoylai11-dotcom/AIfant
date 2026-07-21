// Common JavaScript utilities

// Toast notification
function showToast(msg, type) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.className = 'px-4 py-2 rounded shadow-lg text-sm text-white ' +
        (type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600');
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => el.remove(), 3000);
}

// Format number with commas
function formatNumber(n) {
    if (n == null) return '—';
    return n.toLocaleString();
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('zh-CN');
}

// Format datetime
function formatDateTime(dateStr) {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('zh-CN');
}

// Safe HTML escaping
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Truncate string
function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
}

// Parse integer with null safety
function parseIntOrNull(val) {
    if (val === '' || val === null || val === undefined) return null;
    const n = parseInt(val);
    return isNaN(n) ? null : n;
}
