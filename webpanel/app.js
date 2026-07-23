'use strict';

/* Palmilha Inteligente — painel web da clínica (SPA vanilla JS, pt-BR, sem recursos externos) */

const API_BASE = '/api';
const TOKEN_KEY = 'footscan_token';
const USER_KEY = 'footscan_user';
const CONSENT_VERSION = 'v1';
const OVERLAY_MARGIN_MM = 30;

let currentUser = null;

/* ---------------------------------------------------------------- constantes de domínio */

const MEASURE_FIELDS = [
  ['length_mm', 'Comprimento', 'mm'],
  ['forefoot_width_mm', 'Largura do antepé', 'mm'],
  ['midfoot_width_mm', 'Largura do mediopé', 'mm'],
  ['heel_width_mm', 'Largura do calcanhar', 'mm'],
  ['plantar_area_cm2', 'Área plantar', 'cm²'],
  ['axis_angle_deg', 'Ângulo do eixo', '°'],
];

const COMPARE_FIELDS = [
  ['length_mm', 'Comprimento', 'mm'],
  ['forefoot_width_mm', 'Antepé', 'mm'],
  ['midfoot_width_mm', 'Mediopé', 'mm'],
  ['heel_width_mm', 'Calcanhar', 'mm'],
  ['plantar_area_cm2', 'Área', 'cm²'],
];

const LANDMARK_DEFS = [
  ['toe', 'Ponta do dedo', '#1667b8'],
  ['heel', 'Calcanhar', '#1667b8'],
  ['forefoot_a', 'Antepé A', '#2e7d32'],
  ['forefoot_b', 'Antepé B', '#2e7d32'],
  ['midfoot_a', 'Mediopé A', '#ef6c00'],
  ['midfoot_b', 'Mediopé B', '#ef6c00'],
  ['heel_a', 'Calcanhar A', '#7b1fa2'],
  ['heel_b', 'Calcanhar B', '#7b1fa2'],
];

const STATUS_LABELS = { draft: 'Rascunho', processed: 'Processado', reviewed: 'Revisado' };
const STATUS_CLASSES = { draft: 'badge-gray', processed: 'badge-blue', reviewed: 'badge-green' };
const SEX_LABELS = { F: 'Feminino', M: 'Masculino', outro: 'Outro' };
const SIDE_LABELS = { left: 'Pé Esquerdo', right: 'Pé Direito' };

const PROCESSING_ERRORS = {
  markers_not_found: 'Não foi possível encontrar os 4 marcadores da placa na foto.',
  foot_not_found: 'Não foi possível identificar o pé sobre a placa.',
  invalid_image: 'A imagem enviada é inválida ou está corrompida.',
};
const RECAPTURE_HINT =
  'Dica: refaça a foto com a placa inteira visível, boa iluminação uniforme, sem sombras fortes, ' +
  'com o pé totalmente dentro da área útil e o celular o mais paralelo possível à placa.';

const LGPD_CONSENT_TEXT =
  'Declaro que o(a) paciente foi informado(a) e consentiu com a coleta e o tratamento de seus dados ' +
  'pessoais e das imagens dos seus pés por esta clínica, exclusivamente para fins de avaliação, ' +
  'medição, documentação clínica e confecção de palmilhas personalizadas, conforme a Lei Geral de ' +
  'Proteção de Dados (LGPD — Lei nº 13.709/2018). Os dados serão armazenados com segurança, acessados ' +
  'apenas por profissionais autorizados e poderão ser corrigidos ou eliminados a pedido do titular. ' +
  'As medições geradas são documentos de apoio e não constituem diagnóstico.';

/* ---------------------------------------------------------------- helpers DOM */

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  if (attrs) {
    for (const [key, value] of Object.entries(attrs)) {
      if (value == null || value === false) continue;
      if (key === 'class') node.className = value;
      else if (key.startsWith('on') && typeof value === 'function') {
        node.addEventListener(key.slice(2), value);
      } else if (value === true) node.setAttribute(key, '');
      else node.setAttribute(key, value);
    }
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    node.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return node;
}

function setView(...nodes) {
  const view = document.getElementById('view');
  view.replaceChildren(...nodes);
  window.scrollTo(0, 0);
}

function spinner(label) {
  return el('div', { class: 'loading' },
    el('div', { class: 'spinner' }),
    el('p', { class: 'muted' }, label || 'Carregando...'));
}

function setLoading(btn, loading, text) {
  if (loading) {
    btn.dataset.orig = btn.textContent;
    btn.disabled = true;
    btn.textContent = text || 'Aguarde...';
  } else {
    btn.disabled = false;
    if (btn.dataset.orig) btn.textContent = btn.dataset.orig;
  }
}

function toast(message, type) {
  const container = document.getElementById('toast-container');
  const node = el('div', { class: 'toast toast-' + (type || 'success') }, message);
  container.append(node);
  setTimeout(() => {
    node.classList.add('toast-out');
    setTimeout(() => node.remove(), 350);
  }, 3500);
}

function showModal(title, body, footer) {
  closeModal();
  const overlay = el('div', { class: 'modal-overlay', id: 'modal-overlay' },
    el('div', { class: 'modal', role: 'dialog', 'aria-label': title },
      el('div', { class: 'modal-header' },
        el('h3', null, title),
        el('button', { class: 'modal-close', type: 'button', 'aria-label': 'Fechar', onclick: closeModal }, '×')),
      el('div', { class: 'modal-body' }, body),
      footer ? el('div', { class: 'modal-footer' }, footer) : null));
  document.body.append(overlay);
  return overlay;
}

function closeModal() {
  const overlay = document.getElementById('modal-overlay');
  if (overlay) overlay.remove();
}

function errorView(err, retry) {
  return el('div', { class: 'card error-card' },
    el('h3', null, 'Ocorreu um erro'),
    el('p', null, err && err.message ? err.message : 'Erro inesperado.'),
    retry ? el('button', { class: 'btn btn-primary', type: 'button', onclick: retry }, 'Tentar novamente') : null);
}

/* ---------------------------------------------------------------- formatação */

function fmtNum(value) {
  if (typeof value !== 'number' || !isFinite(value)) return '—';
  return value.toFixed(1).replace('.', ',');
}

function fmtSigned(value) {
  if (typeof value !== 'number' || !isFinite(value)) return '—';
  const sign = value > 0 ? '+' : value < 0 ? '−' : '±';
  return sign + Math.abs(value).toFixed(1).replace('.', ',');
}

function parseDate(value) {
  if (!value) return null;
  let str = String(value);
  if (/T\d{2}:\d{2}/.test(str) && !/(Z|[+-]\d{2}:?\d{2})$/.test(str)) str += 'Z';
  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
}

function fmtDateTime(value) {
  const d = parseDate(value);
  if (!d) return '—';
  return d.toLocaleDateString('pt-BR') + ' ' +
    d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function fmtDateOnly(value) {
  if (!value) return '—';
  const m = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return m[3] + '/' + m[2] + '/' + m[1];
  const d = parseDate(value);
  return d ? d.toLocaleDateString('pt-BR') : '—';
}

function slugify(text) {
  return String(text || '').toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'paciente';
}

function processingErrorText(raw) {
  if (!raw) return '';
  let code = null;
  let message = String(raw);
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.code) { code = parsed.code; message = parsed.message || message; }
  } catch (e) { /* texto simples */ }
  if (!code) {
    const m = message.match(/markers_not_found|foot_not_found|invalid_image/);
    if (m) code = m[0];
  }
  if (code && PROCESSING_ERRORS[code]) return PROCESSING_ERRORS[code];
  return message;
}

/* ---------------------------------------------------------------- auth + API */

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function setToken(token) { localStorage.setItem(TOKEN_KEY, token); }

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  currentUser = null;
}

function logout() {
  clearAuth();
  updateTopbar();
  location.hash = '#/login';
}

async function handleResponse(res, path, asBlob) {
  if (res.status === 401 && !path.startsWith('/auth/login')) {
    clearAuth();
    updateTopbar();
    if (location.hash !== '#/login') location.hash = '#/login';
    throw new Error('Sessão expirada. Faça login novamente.');
  }
  if (!res.ok) {
    let message = 'Erro ' + res.status;
    try {
      const data = await res.json();
      if (data && data.detail != null) {
        if (typeof data.detail === 'string') message = data.detail;
        else if (Array.isArray(data.detail)) {
          message = data.detail.map((d) => d.msg || '').filter(Boolean).join('; ') || 'Dados inválidos.';
        } else if (data.detail.message) message = data.detail.message;
        else message = JSON.stringify(data.detail);
      }
    } catch (e) { /* corpo não-JSON */ }
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  if (asBlob) return { blob: await res.blob(), headers: res.headers };
  if (res.status === 204) return null;
  return res.json();
}

async function api(path, options) {
  const opts = Object.assign({}, options);
  const headers = Object.assign({}, opts.headers || {});
  const token = getToken();
  if (token) headers.Authorization = 'Bearer ' + token;
  if (opts.body && !(opts.body instanceof FormData) && typeof opts.body !== 'string') {
    headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  opts.headers = headers;
  let res;
  try {
    res = await fetch(API_BASE + path, opts);
  } catch (e) {
    throw new Error('Falha de conexão com o servidor. Verifique a rede.');
  }
  return handleResponse(res, path, false);
}

async function apiBlob(path) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = 'Bearer ' + token;
  let res;
  try {
    res = await fetch(API_BASE + path, { headers });
  } catch (e) {
    throw new Error('Falha de conexão com o servidor. Verifique a rede.');
  }
  return handleResponse(res, path, true);
}

/* ---------------------------------------------------------------- roteador */

function updateTopbar() {
  const topbar = document.getElementById('topbar');
  if (getToken()) {
    topbar.classList.remove('hidden');
    document.getElementById('user-name').textContent = currentUser ? currentUser.name : '';
  } else {
    topbar.classList.add('hidden');
  }
}

function route() {
  const hash = location.hash || '#/patients';
  const parts = hash.replace(/^#\/?/, '').split('/');
  if (!getToken() && parts[0] !== 'login') {
    location.hash = '#/login';
    return;
  }
  if (getToken() && parts[0] === 'login') {
    location.hash = '#/patients';
    return;
  }
  closeModal();
  updateTopbar();
  if (parts[0] === 'login') renderLogin();
  else if (parts[0] === 'patient' && parts[1]) renderPatient(parts[1]);
  else if (parts[0] === 'exam' && parts[1]) renderExam(parts[1]);
  else renderPatients();
}

async function init() {
  document.getElementById('btn-logout').addEventListener('click', logout);
  const cached = localStorage.getItem(USER_KEY);
  if (cached) {
    try { currentUser = JSON.parse(cached); } catch (e) { currentUser = null; }
  }
  if (getToken()) {
    try {
      currentUser = await api('/auth/me');
      localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
    } catch (e) { /* 401 já tratado globalmente */ }
  }
  route();
}

window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', init);

/* ---------------------------------------------------------------- tela: login */

function renderLogin() {
  const emailInput = el('input', {
    type: 'email', required: true, autocomplete: 'username', placeholder: 'email@clinica.com.br',
  });
  const passwordInput = el('input', {
    type: 'password', required: true, autocomplete: 'current-password', placeholder: 'Senha',
  });
  const errBox = el('div', { class: 'error-box hidden' });
  const submitBtn = el('button', { class: 'btn btn-primary btn-block', type: 'submit' }, 'Entrar');

  const form = el('form', {
    class: 'login-form',
    onsubmit: async (event) => {
      event.preventDefault();
      errBox.classList.add('hidden');
      setLoading(submitBtn, true, 'Entrando...');
      try {
        const out = await api('/auth/login', {
          method: 'POST',
          body: { email: emailInput.value.trim(), password: passwordInput.value },
        });
        setToken(out.access_token);
        currentUser = out.user;
        localStorage.setItem(USER_KEY, JSON.stringify(out.user));
        location.hash = '#/patients';
      } catch (err) {
        errBox.textContent = err.message;
        errBox.classList.remove('hidden');
      } finally {
        setLoading(submitBtn, false);
      }
    },
  },
    el('label', { class: 'field' }, el('span', { class: 'field-label' }, 'E-mail'), emailInput),
    el('label', { class: 'field' }, el('span', { class: 'field-label' }, 'Senha'), passwordInput),
    submitBtn,
    errBox);

  setView(el('div', { class: 'login-wrap' },
    el('div', { class: 'card login-card' },
      el('img', {
        class: 'login-logo-img', src: 'brand/logo-full.png',
        alt: 'Palmilha Inteligente — Você, livre das dores!',
      }),
      el('p', { class: 'muted login-sub' }, 'Painel da clínica — avaliação e medição dos pés'),
      form,
      el('p', { class: 'login-footnote muted' },
        'Acesso restrito a profissionais autorizados. Dados protegidos conforme a LGPD.'))));
}

/* ---------------------------------------------------------------- tela: pacientes */

function consentBadge(patient) {
  if (patient.consent_accepted_at) {
    return el('span', { class: 'badge badge-green' },
      'Consentimento ' + (patient.consent_version || ''));
  }
  return el('span', { class: 'badge badge-yellow' }, 'Sem consentimento');
}

function renderPatients() {
  const listBox = el('div', { class: 'card table-card' }, spinner('Carregando pacientes...'));
  const searchInput = el('input', {
    type: 'search', class: 'search-input', placeholder: 'Buscar por nome ou documento...',
    'aria-label': 'Buscar pacientes',
  });

  let debounceTimer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => loadList(searchInput.value.trim()), 300);
  });

  async function loadList(search) {
    listBox.replaceChildren(spinner('Carregando pacientes...'));
    try {
      const query = search ? '?search=' + encodeURIComponent(search) : '';
      const patients = await api('/patients' + query);
      if (!patients.length) {
        listBox.replaceChildren(el('p', { class: 'empty' },
          search ? 'Nenhum paciente encontrado para "' + search + '".' : 'Nenhum paciente cadastrado ainda.'));
        return;
      }
      const rows = patients.map((p) => el('tr', {
        class: 'row-link',
        onclick: () => { location.hash = '#/patient/' + p.uuid; },
      },
        el('td', null, el('strong', null, p.name)),
        el('td', null, p.document || '—'),
        el('td', null, p.phone || '—'),
        el('td', null, consentBadge(p)),
        el('td', { class: 'td-actions' },
          el('button', {
            class: 'btn btn-outline btn-sm', type: 'button',
            onclick: (ev) => { ev.stopPropagation(); openPatientForm(p, () => loadList(searchInput.value.trim())); },
          }, 'Editar'),
          !p.consent_accepted_at ? el('button', {
            class: 'btn btn-primary btn-sm', type: 'button',
            onclick: (ev) => { ev.stopPropagation(); openConsentModal(p, () => loadList(searchInput.value.trim())); },
          }, 'Registrar consentimento') : null)));
      listBox.replaceChildren(el('div', { class: 'table-wrap' },
        el('table', null,
          el('thead', null, el('tr', null,
            el('th', null, 'Nome'), el('th', null, 'Documento'), el('th', null, 'Telefone'),
            el('th', null, 'Consentimento'), el('th', null, 'Ações'))),
          el('tbody', null, rows))));
    } catch (err) {
      listBox.replaceChildren(errorView(err, () => loadList(search)));
    }
  }

  setView(
    el('div', { class: 'page-header' },
      el('h2', null, 'Pacientes'),
      el('button', {
        class: 'btn btn-primary', type: 'button',
        onclick: () => openPatientForm(null, () => loadList(searchInput.value.trim())),
      }, 'Novo paciente')),
    el('div', { class: 'search-bar' }, searchInput),
    listBox);

  loadList('');
}

function openPatientForm(patient, onSaved) {
  const isEdit = !!patient;
  const nameInput = el('input', { type: 'text', required: true, value: patient ? patient.name : '' });
  const birthInput = el('input', { type: 'date', value: patient && patient.birth_date ? String(patient.birth_date).slice(0, 10) : '' });
  const sexSelect = el('select', null,
    el('option', { value: '' }, 'Não informado'),
    el('option', { value: 'F', selected: patient && patient.sex === 'F' }, 'Feminino'),
    el('option', { value: 'M', selected: patient && patient.sex === 'M' }, 'Masculino'),
    el('option', { value: 'outro', selected: patient && patient.sex === 'outro' }, 'Outro'));
  const documentInput = el('input', { type: 'text', value: patient ? patient.document || '' : '' });
  const phoneInput = el('input', { type: 'tel', value: patient ? patient.phone || '' : '' });
  const emailInput = el('input', { type: 'email', value: patient ? patient.email || '' : '' });
  const notesInput = el('textarea', { rows: '3' }, patient ? patient.notes || '' : '');
  const errBox = el('div', { class: 'error-box hidden' });
  const saveBtn = el('button', { class: 'btn btn-primary', type: 'submit', form: 'patient-form' },
    isEdit ? 'Salvar alterações' : 'Cadastrar');

  const form = el('form', {
    id: 'patient-form', class: 'form-grid',
    onsubmit: async (event) => {
      event.preventDefault();
      errBox.classList.add('hidden');
      const body = {
        name: nameInput.value.trim(),
        birth_date: birthInput.value || null,
        sex: sexSelect.value || null,
        document: documentInput.value.trim() || null,
        phone: phoneInput.value.trim() || null,
        email: emailInput.value.trim() || null,
        notes: notesInput.value.trim() || null,
      };
      setLoading(saveBtn, true, 'Salvando...');
      try {
        if (isEdit) await api('/patients/' + patient.uuid, { method: 'PUT', body });
        else await api('/patients', { method: 'POST', body });
        closeModal();
        toast(isEdit ? 'Paciente atualizado.' : 'Paciente cadastrado.');
        if (onSaved) onSaved();
      } catch (err) {
        errBox.textContent = err.message;
        errBox.classList.remove('hidden');
        setLoading(saveBtn, false);
      }
    },
  },
    el('label', { class: 'field span-2' }, el('span', { class: 'field-label' }, 'Nome *'), nameInput),
    el('label', { class: 'field' }, el('span', { class: 'field-label' }, 'Nascimento'), birthInput),
    el('label', { class: 'field' }, el('span', { class: 'field-label' }, 'Sexo'), sexSelect),
    el('label', { class: 'field' }, el('span', { class: 'field-label' }, 'Documento (CPF/RG)'), documentInput),
    el('label', { class: 'field' }, el('span', { class: 'field-label' }, 'Telefone'), phoneInput),
    el('label', { class: 'field span-2' }, el('span', { class: 'field-label' }, 'E-mail'), emailInput),
    el('label', { class: 'field span-2' }, el('span', { class: 'field-label' }, 'Observações'), notesInput),
    el('div', { class: 'span-2' }, errBox));

  showModal(isEdit ? 'Editar paciente' : 'Novo paciente', form,
    [el('button', { class: 'btn btn-outline', type: 'button', onclick: closeModal }, 'Cancelar'), saveBtn]);
}

function openConsentModal(patient, onDone) {
  const errBox = el('div', { class: 'error-box hidden' });
  const confirmBtn = el('button', { class: 'btn btn-primary', type: 'button' },
    'Registrar consentimento (' + CONSENT_VERSION + ')');
  confirmBtn.addEventListener('click', async () => {
    errBox.classList.add('hidden');
    setLoading(confirmBtn, true, 'Registrando...');
    try {
      await api('/patients/' + patient.uuid + '/consent', {
        method: 'POST',
        body: { version: CONSENT_VERSION },
      });
      closeModal();
      toast('Consentimento registrado para ' + patient.name + '.');
      if (onDone) onDone();
    } catch (err) {
      errBox.textContent = err.message;
      errBox.classList.remove('hidden');
      setLoading(confirmBtn, false);
    }
  });

  showModal('Consentimento LGPD — ' + patient.name,
    el('div', null,
      el('p', { class: 'consent-text' }, LGPD_CONSENT_TEXT),
      el('p', { class: 'muted' }, 'Versão do termo: ' + CONSENT_VERSION),
      errBox),
    [el('button', { class: 'btn btn-outline', type: 'button', onclick: closeModal }, 'Cancelar'), confirmBtn]);
}

/* ---------------------------------------------------------------- tela: paciente */

async function renderPatient(uuid) {
  setView(spinner('Carregando paciente...'));
  let patient;
  let exams;
  let history;
  try {
    [patient, exams, history] = await Promise.all([
      api('/patients/' + uuid),
      api('/exams?patient_uuid=' + encodeURIComponent(uuid)),
      api('/patients/' + uuid + '/history'),
    ]);
  } catch (err) {
    setView(errorView(err, () => renderPatient(uuid)));
    return;
  }

  const hasConsent = !!patient.consent_accepted_at;

  const infoCard = el('div', { class: 'card' },
    el('div', { class: 'card-header' },
      el('h3', null, 'Dados do paciente'),
      el('div', { class: 'card-header-actions' },
        consentBadge(patient),
        el('button', {
          class: 'btn btn-outline btn-sm', type: 'button',
          onclick: () => openPatientForm(patient, () => renderPatient(uuid)),
        }, 'Editar'))),
    el('div', { class: 'info-grid' },
      infoItem('Nascimento', fmtDateOnly(patient.birth_date)),
      infoItem('Sexo', patient.sex ? SEX_LABELS[patient.sex] || patient.sex : '—'),
      infoItem('Documento', patient.document || '—'),
      infoItem('Telefone', patient.phone || '—'),
      infoItem('E-mail', patient.email || '—'),
      infoItem('Cadastro', fmtDateTime(patient.created_at)),
      hasConsent ? infoItem('Consentimento em', fmtDateTime(patient.consent_accepted_at)) : null,
      patient.notes ? infoItem('Observações', patient.notes, true) : null));

  const newExamBtn = el('button', {
    class: 'btn btn-primary', type: 'button', disabled: !hasConsent,
    title: hasConsent ? '' : 'Registre o consentimento LGPD antes de criar um exame.',
    onclick: () => openNewExamModal(patient),
  }, 'Novo exame');

  const consentWarning = !hasConsent ? el('div', { class: 'warn-box' },
    el('strong', null, 'Novo exame bloqueado: '),
    'é necessário registrar o consentimento LGPD do paciente antes de criar exames. ',
    el('button', {
      class: 'btn btn-primary btn-sm', type: 'button',
      onclick: () => openConsentModal(patient, () => renderPatient(uuid)),
    }, 'Registrar consentimento')) : null;

  const examsCard = el('div', { class: 'card table-card' },
    el('div', { class: 'card-header' }, el('h3', null, 'Exames'), newExamBtn),
    consentWarning,
    exams.length ? el('div', { class: 'table-wrap' },
      el('table', null,
        el('thead', null, el('tr', null,
          el('th', null, 'Data'), el('th', null, 'Status'),
          el('th', null, 'Capturas'), el('th', null, 'Observações'), el('th', null, ''))),
        el('tbody', null, exams.map((exam) => el('tr', {
          class: 'row-link',
          onclick: () => { location.hash = '#/exam/' + exam.uuid; },
        },
          el('td', null, fmtDateTime(exam.created_at)),
          el('td', null, statusBadge(exam.status)),
          el('td', null, capturesSummary(exam)),
          el('td', { class: 'td-ellipsis' }, exam.notes || '—'),
          el('td', { class: 'td-actions' },
            el('button', {
              class: 'btn btn-outline btn-sm', type: 'button',
              onclick: (ev) => { ev.stopPropagation(); location.hash = '#/exam/' + exam.uuid; },
            }, 'Abrir'))))))) :
      el('p', { class: 'empty' }, 'Nenhum exame realizado ainda.'));

  const historyCard = buildHistoryCard(history);

  setView(
    el('div', { class: 'page-header' },
      el('div', null,
        el('a', { class: 'back-link', href: '#/patients' }, '← Pacientes'),
        el('h2', null, patient.name))),
    infoCard,
    examsCard,
    historyCard);
}

function infoItem(label, value, wide) {
  return el('div', { class: 'info-item' + (wide ? ' span-2' : '') },
    el('span', { class: 'info-label' }, label),
    el('span', { class: 'info-value' }, value));
}

function statusBadge(status) {
  return el('span', { class: 'badge ' + (STATUS_CLASSES[status] || 'badge-gray') },
    STATUS_LABELS[status] || status);
}

function capturesSummary(exam) {
  const captures = (exam.captures || []).filter((c) => c.view === 'plantar');
  if (!captures.length) return '—';
  return captures.map((c) => {
    const side = c.foot_side === 'left' ? 'E' : 'D';
    const mark = c.measures ? '✓' : c.error ? '✗' : '…';
    return side + ' ' + mark;
  }).join('  ');
}

function openNewExamModal(patient) {
  const notesInput = el('textarea', { rows: '3', placeholder: 'Observações do exame (opcional)' });
  const errBox = el('div', { class: 'error-box hidden' });
  const createBtn = el('button', { class: 'btn btn-primary', type: 'button' }, 'Criar exame');
  createBtn.addEventListener('click', async () => {
    errBox.classList.add('hidden');
    setLoading(createBtn, true, 'Criando...');
    try {
      const exam = await api('/exams', {
        method: 'POST',
        body: { patient_uuid: patient.uuid, notes: notesInput.value.trim() || null },
      });
      closeModal();
      location.hash = '#/exam/' + exam.uuid;
    } catch (err) {
      errBox.textContent = err.message;
      errBox.classList.remove('hidden');
      setLoading(createBtn, false);
    }
  });
  showModal('Novo exame — ' + patient.name,
    el('div', null,
      el('label', { class: 'field' }, el('span', { class: 'field-label' }, 'Observações'), notesInput),
      errBox),
    [el('button', { class: 'btn btn-outline', type: 'button', onclick: closeModal }, 'Cancelar'), createBtn]);
}

function buildHistoryCard(history) {
  const card = el('div', { class: 'card table-card' },
    el('h3', null, 'Histórico comparativo'),
    el('p', { class: 'muted' }, 'Medidas por exame com variação (Δ) em relação ao exame anterior.'));
  const leftTable = historyTable(history, 'left');
  const rightTable = historyTable(history, 'right');
  if (!leftTable && !rightTable) {
    card.append(el('p', { class: 'empty' }, 'Sem medidas processadas ainda para comparar.'));
    return card;
  }
  if (leftTable) card.append(el('h4', { class: 'history-side' }, SIDE_LABELS.left), leftTable);
  if (rightTable) card.append(el('h4', { class: 'history-side' }, SIDE_LABELS.right), rightTable);
  return card;
}

function historyTable(history, side) {
  const entries = (history || []).filter((h) => h.measures_by_side && h.measures_by_side[side]);
  if (!entries.length) return null;
  let previous = null;
  const rows = entries.map((entry) => {
    const measures = entry.measures_by_side[side];
    const cells = COMPARE_FIELDS.map(([key, , unit]) => {
      const value = measures[key];
      let deltaNode = null;
      if (previous && typeof previous[key] === 'number' && typeof value === 'number') {
        const delta = value - previous[key];
        const cls = delta > 0 ? 'delta delta-pos' : delta < 0 ? 'delta delta-neg' : 'delta';
        deltaNode = el('span', { class: cls }, ' Δ ' + fmtSigned(delta));
      }
      return el('td', null, fmtNum(value) + ' ' + unit, deltaNode);
    });
    previous = measures;
    return el('tr', {
      class: 'row-link',
      onclick: () => { location.hash = '#/exam/' + entry.exam_uuid; },
    }, el('td', null, fmtDateTime(entry.created_at)), cells);
  });
  return el('div', { class: 'table-wrap' },
    el('table', { class: 'history-table' },
      el('thead', null, el('tr', null,
        el('th', null, 'Data'),
        COMPARE_FIELDS.map(([, label]) => el('th', null, label)))),
      el('tbody', null, rows)));
}

/* ---------------------------------------------------------------- tela: exame */

async function renderExam(uuid) {
  setView(spinner('Carregando exame...'));
  let exam;
  let patient;
  try {
    exam = await api('/exams/' + uuid);
    patient = await api('/patients/' + exam.patient_uuid);
  } catch (err) {
    setView(errorView(err, () => renderExam(uuid)));
    return;
  }

  const pdfBtn = el('button', { class: 'btn btn-primary', type: 'button' }, 'Baixar relatório PDF');
  pdfBtn.addEventListener('click', () => downloadReport(exam, patient, pdfBtn));

  const header = el('div', { class: 'page-header' },
    el('div', null,
      el('a', { class: 'back-link', href: '#/patient/' + patient.uuid }, '← ' + patient.name),
      el('h2', null, 'Exame de ' + fmtDateTime(exam.created_at), ' ', statusBadge(exam.status)),
      exam.notes ? el('p', { class: 'muted' }, exam.notes) : null),
    pdfBtn);

  const grid = el('div', { class: 'foot-grid' },
    footCard(exam, 'left'),
    footCard(exam, 'right'));

  setView(header, asymmetryCard(exam.asymmetry), grid);
}

function asymmetryCard(asym) {
  if (!asym) {
    return el('div', { class: 'card asym-card' },
      el('h3', null, 'Assimetria (Esquerdo − Direito)'),
      el('p', { class: 'muted' },
        'Disponível quando as capturas plantares dos dois pés forem processadas com sucesso.'));
  }
  const items = COMPARE_FIELDS.map(([key, label, unit]) => {
    const value = asym[key];
    const cls = typeof value === 'number' && Math.abs(value) >= 3 ? 'asym-value asym-high' : 'asym-value';
    return el('div', { class: 'asym-item' },
      el('span', { class: 'info-label' }, label),
      el('span', { class: cls }, fmtSigned(value) + ' ' + unit));
  });
  return el('div', { class: 'card asym-card' },
    el('h3', null, 'Assimetria (Esquerdo − Direito)'),
    el('div', { class: 'asym-grid' }, items));
}

function footCard(exam, side) {
  const capture = (exam.captures || []).find((c) => c.foot_side === side && c.view === 'plantar');
  const content = el('div', { class: 'foot-card-content' });

  if (capture && capture.error) {
    content.append(el('div', { class: 'error-box' },
      el('strong', null, 'Falha no processamento: '),
      processingErrorText(capture.error),
      el('p', { class: 'hint' }, RECAPTURE_HINT)));
  }

  if (capture && capture.measures) {
    const overlayBox = el('div', { class: 'overlay-box' }, spinner('Carregando overlay...'));
    content.append(overlayBox);
    loadOverlay(exam, capture, overlayBox);
    content.append(measuresTable(capture.measures));
  }

  content.append(uploadBlock(exam, side, capture));

  return el('section', { class: 'card foot-card' },
    el('div', { class: 'card-header' },
      el('h3', null, SIDE_LABELS[side]),
      capture && capture.manually_adjusted
        ? el('span', { class: 'badge badge-purple' }, 'Ajustado manualmente') : null),
    content);
}

function measuresTable(measures) {
  const rows = MEASURE_FIELDS
    .filter(([key]) => typeof measures[key] === 'number')
    .map(([key, label, unit]) => el('tr', null,
      el('td', null, label),
      el('td', { class: 'td-num' }, fmtNum(measures[key]) + ' ' + unit)));
  return el('div', { class: 'table-wrap' },
    el('table', { class: 'measures-table' },
      el('thead', null, el('tr', null, el('th', null, 'Medida'), el('th', { class: 'td-num' }, 'Valor'))),
      el('tbody', null, rows)));
}

async function loadOverlay(exam, capture, box) {
  try {
    const { blob } = await apiBlob('/captures/' + capture.uuid + '/overlay');
    const url = URL.createObjectURL(blob);
    const img = el('img', { src: url, alt: 'Overlay do processamento', class: 'overlay-img' });
    const adjustBtn = el('button', {
      class: 'btn btn-outline btn-sm', type: 'button',
      onclick: () => openLandmarkEditor(exam, capture, box, url),
    }, 'Ajustar pontos manualmente');
    box.replaceChildren(img,
      capture.measures && capture.measures.landmarks
        ? el('div', { class: 'overlay-actions' }, adjustBtn) : el('span'));
  } catch (err) {
    box.replaceChildren(el('div', { class: 'error-box' },
      'Não foi possível carregar o overlay: ' + err.message));
  }
}

/* --------------------------- ajuste manual de landmarks (canvas) */

function openLandmarkEditor(exam, capture, box, overlayUrl) {
  const measures = capture.measures;
  const scale = measures.scale_px_per_mm;
  const points = {};
  for (const [key] of LANDMARK_DEFS) {
    const lm = measures.landmarks ? measures.landmarks[key] : null;
    if (lm && lm.length >= 2) {
      points[key] = {
        x: (lm[0] + OVERLAY_MARGIN_MM) * scale,
        y: (lm[1] + OVERLAY_MARGIN_MM) * scale,
      };
    }
  }
  if (!Object.keys(points).length) {
    toast('Esta captura não possui pontos ajustáveis.', 'error');
    return;
  }

  const canvas = el('canvas', { class: 'lm-canvas' });
  const ctx = canvas.getContext('2d');
  const image = new Image();
  let dragging = null;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0);
    for (const [key, label, color] of LANDMARK_DEFS) {
      const p = points[key];
      if (!p) continue;
      ctx.beginPath();
      ctx.arc(p.x, p.y, dragging === key ? 10 : 8, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.9;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();
      ctx.font = 'bold 13px Arial, sans-serif';
      ctx.fillStyle = color;
      ctx.strokeStyle = 'rgba(255,255,255,0.85)';
      ctx.lineWidth = 3;
      ctx.strokeText(label, p.x + 12, p.y + 4);
      ctx.fillText(label, p.x + 12, p.y + 4);
    }
  }

  function canvasPos(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (canvas.width / rect.width),
      y: (event.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  canvas.addEventListener('pointerdown', (event) => {
    const pos = canvasPos(event);
    const rect = canvas.getBoundingClientRect();
    const hitRadius = 16 * (canvas.width / rect.width);
    let best = null;
    let bestDist = Infinity;
    for (const key of Object.keys(points)) {
      const p = points[key];
      const dist = Math.hypot(p.x - pos.x, p.y - pos.y);
      if (dist <= hitRadius && dist < bestDist) { best = key; bestDist = dist; }
    }
    if (best) {
      dragging = best;
      canvas.setPointerCapture(event.pointerId);
      event.preventDefault();
      draw();
    }
  });

  canvas.addEventListener('pointermove', (event) => {
    if (!dragging) return;
    const pos = canvasPos(event);
    points[dragging].x = Math.min(Math.max(pos.x, 0), canvas.width);
    points[dragging].y = Math.min(Math.max(pos.y, 0), canvas.height);
    event.preventDefault();
    draw();
  });

  const endDrag = () => { dragging = null; draw(); };
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);

  const errBox = el('div', { class: 'error-box hidden' });
  const saveBtn = el('button', { class: 'btn btn-primary btn-sm', type: 'button' }, 'Salvar pontos');
  const cancelBtn = el('button', {
    class: 'btn btn-outline btn-sm', type: 'button',
    onclick: () => renderExam(exam.uuid),
  }, 'Cancelar');

  saveBtn.addEventListener('click', async () => {
    errBox.classList.add('hidden');
    setLoading(saveBtn, true, 'Salvando...');
    const landmarks = {};
    for (const key of Object.keys(points)) {
      landmarks[key] = [
        Math.round((points[key].x / scale - OVERLAY_MARGIN_MM) * 10) / 10,
        Math.round((points[key].y / scale - OVERLAY_MARGIN_MM) * 10) / 10,
      ];
    }
    try {
      await api('/captures/' + capture.uuid + '/landmarks', {
        method: 'PUT',
        body: { landmarks },
      });
      toast('Pontos salvos. Medidas recalculadas.');
      renderExam(exam.uuid);
    } catch (err) {
      errBox.textContent = err.message;
      errBox.classList.remove('hidden');
      setLoading(saveBtn, false);
    }
  });

  const legend = el('div', { class: 'lm-legend' },
    LANDMARK_DEFS.filter(([key]) => points[key]).map(([, label, color]) =>
      el('span', { class: 'lm-legend-item' },
        el('span', { class: 'lm-dot', style: 'background:' + color }), label)));

  image.onload = () => {
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    draw();
  };
  image.src = overlayUrl;

  box.replaceChildren(
    el('p', { class: 'muted lm-help' },
      'Arraste os pontos coloridos para corrigir as posições. O comprimento usa Ponta do dedo e ' +
      'Calcanhar; as larguras usam os pares A/B. Ao salvar, as medidas lineares são recalculadas.'),
    canvas,
    legend,
    el('div', { class: 'overlay-actions' }, saveBtn, cancelBtn, errBox));
}

/* --------------------------- upload de captura */

function uploadBlock(exam, side, existingCapture) {
  const inputId = 'file-' + side + '-' + exam.uuid;
  const fileInput = el('input', { type: 'file', accept: 'image/*', id: inputId, class: 'file-input' });
  const fileName = el('span', { class: 'file-name muted' }, 'Nenhum arquivo selecionado');
  const preview = el('div', { class: 'upload-preview hidden' });
  const errBox = el('div', { class: 'error-box hidden' });
  const sendBtn = el('button', { class: 'btn btn-primary btn-sm', type: 'button', disabled: true },
    existingCapture ? 'Substituir e reprocessar' : 'Enviar e processar');
  let previewUrl = null;

  fileInput.addEventListener('change', () => {
    errBox.classList.add('hidden');
    const file = fileInput.files && fileInput.files[0];
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    if (!file) {
      fileName.textContent = 'Nenhum arquivo selecionado';
      preview.classList.add('hidden');
      preview.replaceChildren();
      sendBtn.disabled = true;
      return;
    }
    fileName.textContent = file.name;
    previewUrl = URL.createObjectURL(file);
    preview.replaceChildren(el('img', { src: previewUrl, alt: 'Pré-visualização da captura', class: 'preview-img' }));
    preview.classList.remove('hidden');
    sendBtn.disabled = false;
  });

  sendBtn.addEventListener('click', async () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    errBox.classList.add('hidden');
    setLoading(sendBtn, true, 'Enviando e processando...');
    const formData = new FormData();
    formData.append('foot_side', side);
    formData.append('view', 'plantar');
    formData.append('file', file);
    try {
      const capture = await api('/exams/' + exam.uuid + '/captures', { method: 'POST', body: formData });
      if (capture && capture.error) {
        toast('Imagem enviada, mas o processamento falhou. Veja o aviso no cartão do pé.', 'error');
      } else {
        toast('Captura processada com sucesso.');
      }
      renderExam(exam.uuid);
    } catch (err) {
      errBox.textContent = err.message;
      errBox.classList.remove('hidden');
      setLoading(sendBtn, false);
    }
  });

  return el('div', { class: 'upload-block' },
    el('h4', null, existingCapture ? 'Nova captura (substitui a atual)' : 'Captura plantar'),
    el('div', { class: 'upload-row' },
      el('label', { class: 'btn btn-outline btn-sm file-label', for: inputId }, 'Escolher imagem'),
      fileInput,
      fileName),
    preview,
    el('div', { class: 'upload-row' }, sendBtn),
    errBox);
}

/* --------------------------- download do relatório PDF */

async function downloadReport(exam, patient, btn) {
  setLoading(btn, true, 'Gerando PDF...');
  try {
    const { blob, headers } = await apiBlob('/exams/' + exam.uuid + '/report.pdf');
    let filename = 'relatorio_' + slugify(patient.name) + '.pdf';
    const disposition = headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match) filename = match[1];
    const url = URL.createObjectURL(blob);
    const link = el('a', { href: url, download: filename });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    toast('Relatório baixado.');
  } catch (err) {
    toast('Falha ao baixar o relatório: ' + err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
}
