'use strict';
// Flask serves the interface and API from the same origin.
// Port 8000 remains available for the optional separate frontend server.
const API = location.port === '8000' ? 'http://localhost:5000/api' : `${location.origin}/api`;
const $ = (selector) => document.querySelector(selector);
let token = localStorage.getItem('estudiantes.token');
let user = null, registering = false, page = 1, editing = null, listVersion = 0;
let refreshTimer, searchTimer;

function toast(message, failure = false) {
  const item = document.createElement('div');
  item.className = `toast${failure ? ' failure' : ''}`;
  item.textContent = message;
  $('#toasts').append(item);
  setTimeout(() => item.remove(), 5500);
}

function clearSession() {
  token = null; user = null; listVersion++;
  localStorage.removeItem('estudiantes.token');
  clearInterval(refreshTimer);
  $('#workspace').hidden = true; $('#session').hidden = true; $('#auth').hidden = false;
  $('#students').replaceChildren(); $('#career-list').replaceChildren();
  if ($('#student-dialog').open) $('#student-dialog').close();
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers }
    });
  } catch { throw new Error('No se pudo conectar. Verifica que Flask esté iniciado y vuelve a intentarlo.'); }
  const data = await response.json().catch(() => ({ error: 'Respuesta del servidor inválida.' }));
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') clearSession();
    const error = new Error(data.error || 'No fue posible completar la operación.');
    error.fields = data.errores;
    throw error;
  }
  return data;
}

function errors(form, fields = {}) {
  form.querySelectorAll('[data-error]').forEach(node => { node.textContent = fields[node.dataset.error] || ''; });
  form.querySelectorAll('input').forEach(input => input.setAttribute('aria-invalid', String(Boolean(fields[input.name]))));
}

const nameRegex = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ -][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*$/;
function validate(input, student = false) {
  input.setCustomValidity('');
  const value = input.value.trim();
  let message = '';
  if (student && ['nombre', 'apellido'].includes(input.name) && (!nameRegex.test(value) || value.length < 2)) message = 'Usa entre 2 y 60 letras, espacios o guiones.';
  if (student && input.name === 'carrera' && (value.length < 3 || !/^[\p{L}\p{N}_ .()&-]+$/u.test(value))) message = 'Usa entre 3 y 100 caracteres válidos.';
  if (student && input.name === 'telefono' && value && (!/^\+?[0-9 ()-]{7,25}$/.test(value) || !/^\d{7,15}$/.test(value.replace(/\D/g, '')))) message = 'Usa entre 7 y 15 dígitos con formato telefónico.';
  if (input.name === 'password' && new TextEncoder().encode(input.value).length > 72) message = 'La contraseña admite hasta 72 bytes UTF-8.';
  input.setCustomValidity(message);
  const target = input.closest('label').querySelector('[data-error]');
  if (target) target.textContent = input.validity.valid ? '' : input.validationMessage;
  input.setAttribute('aria-invalid', String(!input.validity.valid));
  return input.validity.valid;
}
document.querySelectorAll('form input').forEach(input => {
  input.addEventListener('input', () => validate(input, input.form.id === 'student-form'));
  input.addEventListener('blur', () => validate(input, input.form.id === 'student-form'));
});

function authMode(register) {
  registering = register;
  $('#auth-form').reset(); errors($('#auth-form'));
  $('#auth-form').querySelectorAll('input').forEach(input => input.setCustomValidity(''));
  $('#register-email').hidden = !register;
  const email = $('#auth-form').elements.email;
  email.disabled = !register; email.required = register;
  $('#auth-title').textContent = register ? 'Crear cuenta' : 'Bienvenido';
  $('#auth-submit').textContent = register ? 'Crear cuenta' : 'Iniciar sesión';
  $('#auth-form').elements.password.autocomplete = register ? 'new-password' : 'current-password';
  $('#login-tab').setAttribute('aria-pressed', String(!register));
  $('#register-tab').setAttribute('aria-pressed', String(register));
}
$('#login-tab').onclick = () => authMode(false);
$('#register-tab').onclick = () => authMode(true);

$('#auth-form').addEventListener('submit', async event => {
  event.preventDefault(); const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  if (!registering) delete data.email;
  $('#auth-submit').disabled = true; errors(form);
  try {
    const result = await api(registering ? '/auth/registro' : '/auth/login', { method: 'POST', body: JSON.stringify(data) });
    if (registering) { authMode(false); toast('Cuenta creada. Ya puedes iniciar sesión.'); }
    else {
      token = result.token; localStorage.setItem('estudiantes.token', token);
      form.reset(); await enter();
    }
  } catch (error) { errors(form, { general: error.message, ...error.fields }); }
  finally { $('#auth-submit').disabled = false; }
});

async function enter() {
  const profile = await api('/auth/perfil'); user = profile.usuario;
  $('#identity').textContent = `${user.username} · ${user.rol === 'admin' ? 'Administrador' : 'Usuario'}`;
  $('#auth').hidden = true; $('#workspace').hidden = false; $('#session').hidden = false;
  page = 1;
  await Promise.all([loadStudents(), loadStats()]);
  clearInterval(refreshTimer);
  refreshTimer = setInterval(() => { if (user) loadStats().catch(error => toast(error.message, true)); }, 30000);
}

$('#logout').onclick = async () => {
  $('#logout').disabled = true;
  try { await api('/auth/logout', { method: 'POST' }); clearSession(); toast('Sesión cerrada.'); }
  catch (error) { toast(error.message, true); }
  finally { $('#logout').disabled = false; }
};

function cell(row, text, secondary) {
  const td = row.insertCell(); td.textContent = text;
  if (secondary) { const small = document.createElement('small'); small.textContent = secondary; td.append(small); }
  return td;
}

async function loadStudents() {
  const version = ++listVersion;
  $('#list-status').textContent = 'Cargando estudiantes…';
  $('#previous').disabled = true; $('#next').disabled = true;
  try {
    const params = new URLSearchParams({ page, per_page: $('#page-size').value, search: $('#search').value.trim(), orden: $('#sort').value, direccion: $('#direction').value });
    const data = await api(`/estudiantes?${params}`);
    if (version !== listVersion || !user) return;
    const info = data.paginacion;
    if (page > 1 && page > info.total_pages) { page = Math.max(1, info.total_pages); return loadStudents(); }
    $('#students').replaceChildren();
    for (const student of data.estudiantes) {
      const row = document.createElement('tr');
      cell(row, `${student.nombre} ${student.apellido}`, `Registro #${student.id}`);
      cell(row, `${student.edad}`); cell(row, student.carrera); cell(row, student.email, student.telefono);
      const actions = cell(row, ''); const buttons = document.createElement('div'); buttons.className = 'row-actions'; actions.append(buttons);
      const edit = document.createElement('button'); edit.textContent = 'Editar'; edit.className = 'secondary'; edit.onclick = () => openStudent(student.id); buttons.append(edit);
      if (user.rol === 'admin') {
        const remove = document.createElement('button'); remove.textContent = 'Eliminar'; remove.className = 'danger';
        remove.onclick = async () => {
          if (!confirm(`¿Eliminar a ${student.nombre} ${student.apellido}?`)) return;
          remove.disabled = true;
          try { await api(`/estudiantes/${student.id}`, { method: 'DELETE' }); toast('Estudiante eliminado.'); await Promise.all([loadStudents(), loadStats()]); }
          catch (error) { toast(error.message, true); remove.disabled = false; }
        }; buttons.append(remove);
      }
      $('#students').append(row);
    }
    $('#list-status').textContent = info.total_items ? `${info.total_items} estudiantes encontrados` : 'No hay estudiantes que coincidan. Puedes registrar uno nuevo o cambiar la búsqueda.';
    $('#page-info').textContent = `Página ${info.total_pages ? page : 0} de ${info.total_pages} · ${info.total_items} registros`;
    $('#previous').disabled = !info.has_prev; $('#next').disabled = !info.has_next;
  } catch (error) { if (version === listVersion) { $('#list-status').textContent = error.message; $('#students').replaceChildren(); $('#page-info').textContent = ''; } }
}

async function loadStats() {
  const stats = await api('/estudiantes/stats/general');
  if (!user) return;
  $('#stat-total').textContent = stats.total_estudiantes;
  $('#stat-average').textContent = Number(stats.promedio_edad).toLocaleString('es-CO', { maximumFractionDigits: 1 });
  $('#stat-range').textContent = stats.total_estudiantes ? `${stats.edad_minima}–${stats.edad_maxima}` : '—';
  $('#stat-careers').textContent = stats.estudiantes_por_carrera.length;
  $('#career-list').replaceChildren();
  for (const career of stats.estudiantes_por_carrera) {
    const li = document.createElement('li'); const count = document.createElement('strong');
    li.append(document.createTextNode(career.carrera)); count.textContent = career.cantidad; li.append(count); $('#career-list').append(li);
  }
  if (!stats.total_estudiantes) $('#career-list').textContent = 'Las carreras aparecerán al registrar estudiantes.';
}

$('#search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { page = 1; loadStudents(); }, 350); };
['sort', 'direction', 'page-size'].forEach(id => { $(`#${id}`).onchange = () => { page = 1; loadStudents(); }; });
$('#previous').onclick = () => { page--; loadStudents(); };
$('#next').onclick = () => { page++; loadStudents(); };

async function openStudent(id = null) {
  const form = $('#student-form'); form.reset(); errors(form);
  form.querySelectorAll('input').forEach(input => input.setCustomValidity(''));
  try {
    if (id !== null) {
      const student = await api(`/estudiantes/${id}`);
      for (const key of ['nombre', 'apellido', 'edad', 'carrera', 'email', 'telefono']) form.elements[key].value = student[key];
    }
    editing = id; $('#student-title').textContent = id === null ? 'Nuevo estudiante' : 'Editar estudiante';
    $('#student-dialog').showModal();
  } catch (error) { toast(error.message, true); }
}
$('#new-student').onclick = () => openStudent();
$('#close-dialog').onclick = $('#cancel-student').onclick = () => $('#student-dialog').close();
$('#student-form').onsubmit = async event => {
  event.preventDefault(); const form = event.currentTarget;
  const valid = [...form.querySelectorAll('input')].map(input => validate(input, true)).every(Boolean);
  if (!valid || !form.reportValidity()) return;
  const data = Object.fromEntries(new FormData(form)); data.edad = Number(data.edad);
  const submit = form.querySelector('[type=submit]'); submit.disabled = true; errors(form);
  try {
    await api(editing === null ? '/estudiantes' : `/estudiantes/${editing}`, { method: editing === null ? 'POST' : 'PUT', body: JSON.stringify(data) });
    $('#student-dialog').close(); toast(editing === null ? 'Estudiante registrado.' : 'Cambios guardados.');
    await Promise.all([loadStudents(), loadStats()]);
  } catch (error) { errors(form, { general: error.message, ...error.fields }); }
  finally { submit.disabled = false; }
};

window.addEventListener('storage', event => {
  if (event.key === 'estudiantes.token') { clearSession(); toast('La sesión cambió en otra pestaña. Inicia sesión nuevamente.'); }
});
if (token) enter().catch(error => { clearSession(); toast(error.message, true); });
