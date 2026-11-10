const API = '/api';

async function request(method, path, body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== null) opts.body = JSON.stringify(body);
    const res = await fetch(API + path, opts);
    if (res.status === 204) return null;
    const json = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) {
        let msg = json.detail;
        if (Array.isArray(msg)) msg = msg.map(e => e.msg).join('; ');
        throw new Error(msg || 'Erro desconhecido');
    }
    return json;
}

const api = {
    items:        (kind)   => request('GET', '/items' + (kind ? `?kind=${kind}` : '')),
    item:         (id)     => request('GET', `/items/${id}`),
    createItem:   (d)      => request('POST', '/items', d),
    updateItem:   (id, d)  => request('PUT', `/items/${id}`, d),
    deleteItem:   (id)     => request('DELETE', `/items/${id}`),
    itemCost:     (id)     => request('GET', `/items/${id}/cost`),
    purchase:     (d)      => request('POST', '/stock/purchase', d),
    adjust:       (d)      => request('POST', '/stock/adjust', d),
    movements:    (q = '') => request('GET', '/stock/movements' + q),
    produce:      (d)      => request('POST', '/production', d),
    productions:  ()       => request('GET', '/production'),
    registerSales:(d)      => request('POST', '/sales', d),
    sales:        ()       => request('GET', '/sales'),
    undoSale:     (id)     => request('DELETE', `/sales/${id}`),
    summary:      ()       => request('GET', '/reports/summary'),
    replenishment:()       => request('GET', '/reports/replenishment'),
};

// ── formatação ────────────────────────────────────────────────────────────────
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const brl = v => v == null ? '—' : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const num = (v, d = 3) => v == null ? '—' : Number(v).toLocaleString('pt-BR', { maximumFractionDigits: d });
const qty = (v, unit) => v == null ? '—' : `${num(v, ['un', 'g', 'mL'].includes(unit) ? 1 : 3)} ${unit || ''}`;
const pct = v => v == null ? '—' : `${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
const dt  = v => v ? new Date(v).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
const todayISO = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };
const parseNum = s => { const v = parseFloat(String(s ?? '').replace(',', '.')); return isNaN(v) ? null : v; };
const norm = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();

// ── unidades (g↔kg, mL↔L) ─────────────────────────────────────────────────────
const UNIT_FACTOR = { kg: 1000, g: 1, L: 1000, mL: 1, un: 1 };
const UNIT_OPTIONS = { kg: ['kg', 'g'], g: ['g', 'kg'], L: ['L', 'mL'], mL: ['mL', 'L'], un: ['un'] };
const convertQty = (q, from, to) => q == null ? null : +(q * UNIT_FACTOR[from] / UNIT_FACTOR[to]).toFixed(6);
// Unidade mais fácil de ler: 0,3 kg → g; 0,15 L → mL
const friendlyUnit = (q, unit) => (unit === 'kg' && q > 0 && q < 1) ? 'g' : (unit === 'L' && q > 0 && q < 1) ? 'mL' : unit;
const qtyF = (q, unit) => { if (q == null) return '—'; const u = friendlyUnit(Math.abs(q), unit); return qty(convertQty(q, unit, u), u); };
// Unidades aceitas por um item: as do estoque + (porção com peso) as do peso: un, g, kg
const itemUnits = it => {
    const u = [...(UNIT_OPTIONS[it.unit] || [it.unit])];
    return (it.unit === 'un' && it.portion_size && it.portion_unit) ? [...u, ...UNIT_OPTIONS[it.portion_unit]] : u;
};
// quantidade digitada → unidade de estoque do item (300 g de porção de 300 g → 1 un)
function toStock(q, from, it) {
    if (q == null || !from || from === it.unit) return q;
    if ((UNIT_OPTIONS[it.unit] || []).includes(from)) return convertQty(q, from, it.unit);
    return +(convertQty(q, from, it.portion_unit) / it.portion_size).toFixed(6);
}
const unitSelectFor = (it, selected, attrs = '') =>
    `<select class="form-select form-select-sm" style="width:auto" ${attrs}>${itemUnits(it).map(u => `<option ${u === selected ? 'selected' : ''}>${u}</option>`).join('')}</select>`;
// Preço por unidade legível: itens em g/mL mostram o preço por kg/L (R$ 0,0113/g → R$ 11,31/kg)
const unitPrice = (v, unit) => v == null ? '—'
    : unit === 'g' ? `${brl(v * 1000)}/kg` : unit === 'mL' ? `${brl(v * 1000)}/L` : `${brl(v)}/${unit}`;
const unitSelect =(base, selected, attrs = '') =>
    `<select class="form-select form-select-sm" style="width:auto" ${attrs}>${(UNIT_OPTIONS[base] || [base]).map(u => `<option ${u === selected ? 'selected' : ''}>${u}</option>`).join('')}</select>`;

const KIND_LABEL ={ compra: 'Comprado', producao: 'Produzido', venda: 'Prato' };
const MOV_LABEL = {
    compra: ['Compra', 'success'], producao_entrada: ['Produção (entrada)', 'primary'],
    producao_consumo: ['Produção (consumo)', 'secondary'], venda: ['Venda', 'danger'],
    ajuste: ['Contagem', 'warning'],
};

// ── layout ────────────────────────────────────────────────────────────────────
function renderNav(active) {
    const links = [
        ['index', 'speedometer2', 'Painel'], ['vendas', 'cart3', 'Vendas'],
        ['producao', 'fire', 'Produção'], ['estoque', 'box-seam', 'Estoque'],
        ['reposicao', 'clipboard-check', 'Reposição'], ['itens', 'journal-richtext', 'Itens e fichas'],
    ];
    document.getElementById('nav').innerHTML = `
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container">
        <a class="navbar-brand" href="/index.html"><i class="bi bi-shop"></i> Cozinha <small class="fw-normal text-secondary fs-6" id="app-version"></small></a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navc"><span class="navbar-toggler-icon"></span></button>
        <div class="collapse navbar-collapse" id="navc"><ul class="navbar-nav ms-auto">
          ${links.map(([p, i, l]) => `<li class="nav-item"><a class="nav-link ${p === active ? 'active' : ''}" href="/${p}.html"><i class="bi bi-${i}"></i> ${l}</a></li>`).join('')}
        </ul></div>
      </div>
    </nav>`;
    request('GET', '/version')
        .then(v => { document.getElementById('app-version').textContent = 'v' + v.version; })
        .catch(() => {});
}

function toast(msg, type = 'success') {
    const c = document.getElementById('toast-container');
    const id = 't' + Date.now() + Math.random().toString(16).slice(2);
    const color = { success: 'bg-success', error: 'bg-danger', warn: 'bg-warning text-dark' }[type] || 'bg-secondary';
    c.insertAdjacentHTML('beforeend', `
      <div id="${id}" class="toast align-items-center text-white ${color} border-0 mb-2" role="alert">
        <div class="d-flex"><div class="toast-body">${esc(msg)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>
      </div>`);
    const el = document.getElementById(id);
    new bootstrap.Toast(el, { delay: type === 'warn' ? 8000 : 4000 }).show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
}

async function safe(fn) {
    try { return await fn(); } catch (e) { toast(e.message, 'error'); }
}
