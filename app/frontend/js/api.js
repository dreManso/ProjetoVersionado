const API = '/api';

async function request(method, path, body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== null) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    if (res.status === 204) return null;
    const json = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(json.detail || 'Erro desconhecido');
    return json;
}

const api = {
    // ingredientes
    getIngredients:    ()       => request('GET',    '/ingredients'),
    createIngredient:  (data)   => request('POST',   '/ingredients', data),
    updateIngredient:  (id, d)  => request('PUT',    `/ingredients/${id}`, d),
    deleteIngredient:  (id)     => request('DELETE', `/ingredients/${id}`),
    addStock:          (id, d)  => request('POST',   `/ingredients/${id}/stock`, d),
    getMovements:      (id)     => request('GET',    `/ingredients/${id}/movements`),

    // preparações
    getDishes:    ()      => request('GET',    '/dishes'),
    getDish:      (id)    => request('GET',    `/dishes/${id}`),
    createDish:   (data)  => request('POST',   '/dishes', data),
    updateDish:   (id, d) => request('PUT',    `/dishes/${id}`, d),
    deleteDish:   (id)    => request('DELETE', `/dishes/${id}`),
    getDishCost:  (id)    => request('GET',    `/dishes/${id}/cost`),

    // vendas
    getSales:       ()     => request('GET',  '/sales'),
    registerSale:   (data) => request('POST', '/sales', data),

    // relatórios
    getSummary:      () => request('GET', '/reports/summary'),
    getStockAlerts:  () => request('GET', '/reports/stock-alerts'),
    getDishCosts:    () => request('GET', '/reports/dish-costs'),
    getMovementsAll: () => request('GET', '/reports/movements'),
};

function brl(v) {
    if (v == null) return '—';
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}
function num(v, dec = 3) {
    if (v == null) return '—';
    return Number(v).toLocaleString('pt-BR', { maximumFractionDigits: dec });
}
function pct(v) {
    if (v == null) return '—';
    return v.toFixed(1) + '%';
}

function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const id = 'toast-' + Date.now();
    const color = type === 'success' ? 'bg-success' : 'bg-danger';
    container.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="toast align-items-center text-white ${color} border-0 mb-2" role="alert">
            <div class="d-flex">
                <div class="toast-body">${msg}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>`);
    const el = document.getElementById(id);
    new bootstrap.Toast(el, { delay: 3500 }).show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
}
