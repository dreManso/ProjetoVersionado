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
    settings:     ()       => request('GET', '/settings'),
    saveSettings: (d)      => request('PUT', '/settings', d),
};

// ── formatação ────────────────────────────────────────────────────────────────
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const brl = v => v == null ? '—' : Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const num = (v, d = 3) => {
    if (v == null) return '—';
    const n = Math.abs(v) < 0.5 * 10 ** -d ? 0 : Number(v);   // evita "-0"
    return n.toLocaleString('pt-BR', { maximumFractionDigits: d });
};
const qty = (v, unit) => v == null ? '—' : `${num(v, ['un', 'g', 'mL'].includes(unit) ? 1 : 3)} ${unit || ''}`;
const pct = v => v == null ? '—' : `${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
const dt  = v => v ? new Date(v).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';
const todayISO = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };
// ── calculadora: campos de número aceitam contas (4700+2000, 3*500, 21,60/24, 10%) ──
function evalExpr(s) {
    const src = String(s).replace(/\s+/g, '').replace(/[x×]/gi, '*').replace(/÷/g, '/').replace(/[−–]/g, '-');
    let i = 0;
    const peek = () => src[i];
    function number() {
        const m = src.slice(i).match(/^\d+(?:[.,]\d+)*|^[.,]\d+/);
        if (!m) throw new Error('número');
        i += m[0].length;
        let t = m[0];
        if (t.includes(',')) t = t.replace(/\./g, '').replace(',', '.');          // 1.234,56
        else if ((t.match(/\./g) || []).length > 1) t = t.replace(/\./g, '');    // 1.234.567
        return parseFloat(t);
    }
    function factor() {
        if (peek() === '+') { i++; return factor(); }
        if (peek() === '-') { i++; return -factor(); }
        let v;
        if (peek() === '(') { i++; v = expr(); if (peek() !== ')') throw new Error(')'); i++; }
        else v = number();
        if (peek() === '%') { i++; v /= 100; }
        return v;
    }
    function term() {
        let v = factor();
        while (peek() === '*' || peek() === '/') { const op = src[i++]; const r = factor(); v = op === '*' ? v * r : v / r; }
        return v;
    }
    function expr() {
        let v = term();
        while (peek() === '+' || peek() === '-') { const op = src[i++]; const r = term(); v = op === '+' ? v + r : v - r; }
        return v;
    }
    const v = expr();
    if (i !== src.length || !isFinite(v)) throw new Error('conta incompleta');
    return +v.toFixed(6);
}
const hasMath = s => /\d\s*[-+*/x×÷−%]|[()]/i.test(String(s ?? '').trim().replace(/^[-−]/, ''));
const parseNum = s => {
    const t = String(s ?? '').trim();
    if (!t) return null;
    try { return evalExpr(t); } catch { const v = parseFloat(t.replace(',', '.')); return isNaN(v) ? null : v; }
};
const numToField = v => String(+v.toFixed(4)).replace('.', ',');
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

// ── calculadora integrada aos campos de número ─────────────────────────────────
(function setupCalculator() {
    const SEL = 'input[inputmode="decimal"], input[inputmode="numeric"]';
    let field = null, expr = '';
    const make = (id, cls, html = '') => { const e = document.createElement('div'); e.id = id; e.className = cls; e.innerHTML = html; return e; };
    const hint = make('calc-hint', 'calc-hint d-none');
    const btn = make('calc-btn', 'calc-btn d-none', '<i class="bi bi-calculator"></i>');
    btn.title = 'Calculadora';
    const KEYS = ['7', '8', '9', '÷', '4', '5', '6', '×', '1', '2', '3', '−', '0', ',', '%', '+', '(', ')', '⌫', 'C'];
    const panel = make('calc-panel', 'calc-panel shadow d-none', `
        <div class="calc-display"><div class="calc-expr" id="calc-expr">&nbsp;</div><div class="calc-result" id="calc-result">0</div></div>
        <div class="calc-keys">${KEYS.map(k => `<button type="button" tabindex="-1" data-k="${k}" class="btn ${'÷×−+%()'.includes(k) ? 'btn-outline-primary' : k === 'C' || k === '⌫' ? 'btn-outline-danger' : 'btn-light'}">${k}</button>`).join('')}</div>
        <div class="d-flex gap-2 mt-2">
          <button type="button" tabindex="-1" data-k="close" class="btn btn-secondary flex-fill">Fechar</button>
          <button type="button" tabindex="-1" data-k="use" class="btn btn-success flex-fill"><i class="bi bi-check-lg"></i> Usar</button>
        </div>`);
    // não tirar o foco do campo ao clicar na calculadora (funciona também dentro das janelas)
    [btn, panel].forEach(e => e.addEventListener('mousedown', ev => ev.preventDefault()));

    const fmt = v => Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 4 });
    function place(el, below) {
        if (!field) return;
        const r = field.getBoundingClientRect();
        if (below) {
            const w = 260, left = Math.min(Math.max(8, r.right - w), window.innerWidth - w - 8);
            const top = r.bottom + 6 + 330 > window.innerHeight ? Math.max(8, r.top - 336) : r.bottom + 6;
            Object.assign(el.style, { left: left + 'px', top: top + 'px' });
        } else Object.assign(el.style, { left: (r.right - 30) + 'px', top: (r.top + (r.height - 26) / 2) + 'px' });
    }
    function showHint() {
        if (!field) return;
        const v = field.value;
        let txt = '';
        if (hasMath(v)) { try { txt = '= ' + fmt(evalExpr(v)); } catch { txt = 'conta incompleta'; } }
        hint.textContent = txt;
        hint.classList.toggle('d-none', !txt);
        if (txt) { const r = field.getBoundingClientRect(); Object.assign(hint.style, { left: r.left + 'px', top: (r.bottom + 2) + 'px' }); }
    }
    // troca a conta pelo resultado e avisa a tela (os cálculos dela se atualizam)
    function commit(input, value) {
        input.value = numToField(value);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function resolveField(input) {
        if (!hasMath(input.value)) return;
        try { commit(input, evalExpr(input.value)); } catch { /* deixa como está */ }
    }
    function renderPanel() {
        document.getElementById('calc-expr').textContent = expr || ' ';
        let r = '';
        try { r = expr ? fmt(evalExpr(expr)) : '0'; } catch { r = '…'; }
        document.getElementById('calc-result').textContent = r;
    }
    function openPanel() {
        if (!field) return;
        expr = field.value.trim();
        renderPanel(); place(panel, true);
        panel.classList.remove('d-none'); btn.classList.add('d-none');
    }
    const closePanel = () => panel.classList.add('d-none');
    btn.addEventListener('click', openPanel);
    panel.addEventListener('click', ev => {
        const k = ev.target.closest('button')?.dataset.k;
        if (!k) return;
        if (k === 'close') return closePanel();
        if (k === 'use') {
            try { if (field && expr) commit(field, evalExpr(expr)); closePanel(); }
            catch { document.getElementById('calc-result').textContent = 'conta incompleta'; }
            return;
        }
        if (k === 'C') expr = '';
        else if (k === '⌫') expr = expr.slice(0, -1);
        else expr += ({ '÷': '/', '×': '*', '−': '-' }[k] || k);
        renderPanel();
    });

    document.addEventListener('DOMContentLoaded', () => document.body.append(hint, btn, panel));
    document.addEventListener('focusin', ev => {
        if (!ev.target.matches || !ev.target.matches(SEL)) return;
        if (field !== ev.target) closePanel();
        field = ev.target;
        field.dataset.padOrig = field.style.paddingRight;
        field.style.paddingRight = '32px';   // espaço para o botão não cobrir os números
        place(btn, false); btn.classList.remove('d-none'); showHint();
    });
    document.addEventListener('focusout', ev => {
        if (ev.target !== field) return;
        resolveField(field);
        field.style.paddingRight = field.dataset.padOrig || '';
        btn.classList.add('d-none'); hint.classList.add('d-none');
    });
    document.addEventListener('input', ev => { if (ev.target === field) showHint(); });
    document.addEventListener('keydown', ev => {
        if (ev.key === 'Enter' && ev.target.matches && ev.target.matches(SEL)) resolveField(ev.target);
        if (ev.key === 'Escape') closePanel();
    });
    // a janela rolou: reposiciona ou fecha
    window.addEventListener('scroll', () => { closePanel(); if (field && document.activeElement === field) place(btn, false); hint.classList.add('d-none'); }, true);
})();
