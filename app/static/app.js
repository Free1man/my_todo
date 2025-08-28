// Tiny client for the API (same origin)
const state = {
  token: localStorage.getItem('token') || '',
  username: localStorage.getItem('username') || ''
};

const els = {
  auth: document.getElementById('auth-section'),
  app: document.getElementById('app-section'),
  whoami: document.getElementById('whoami'),
  regForm: document.getElementById('register-form'),
  loginForm: document.getElementById('login-form'),
  addForm: document.getElementById('add-form'),
  newText: document.getElementById('new-text'),
  list: document.getElementById('todo-list'),
  logout: document.getElementById('logout-btn'),
  toast: document.getElementById('toast'),
};

function showToast(msg, ms=2000){
  els.toast.textContent = msg;
  els.toast.classList.remove('hidden');
  setTimeout(()=>els.toast.classList.add('hidden'), ms);
}

function setLoggedIn(username, token){
  state.username = username;
  state.token = token;
  localStorage.setItem('username', username || '');
  localStorage.setItem('token', token || '');
  updateView();
}

function updateView(){
  const loggedIn = !!state.token;
  els.auth.classList.toggle('hidden', loggedIn);
  els.app.classList.toggle('hidden', !loggedIn);
  els.whoami.textContent = loggedIn ? `Hello, ${state.username}` : '';
  if (loggedIn) loadTodos();
}

async function api(path, opts={}){
  const headers = Object.assign({'Content-Type':'application/json'}, opts.headers || {});
  if (state.token) headers['Authorization'] = 'Bearer ' + state.token;
  const res = await fetch(path, Object.assign({}, opts, {headers}));
  if (!res.ok){
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

// Register
els.regForm.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  try {
    await api('/register', {method:'POST', body: JSON.stringify({username, password})});
    showToast('Registered. You can login now.');
    els.loginForm.querySelector('#login-username').value = username;
  } catch (e){ showToast('Register failed'); console.error(e); }
});

// Login
els.loginForm.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  try {
    const {access_token} = await api('/login', {method:'POST', body: JSON.stringify({username, password})});
    setLoggedIn(username, access_token);
    showToast('Signed in');
  } catch (e){ showToast('Login failed'); console.error(e); }
});

// Logout
els.logout.addEventListener('click', ()=>{
  setLoggedIn('', '');
  els.list.innerHTML='';
  showToast('Logged out');
});

// Add todo
els.addForm.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const text = els.newText.value.trim();
  if (!text) return;
  try {
    const item = await api('/todos', {method:'POST', body: JSON.stringify({text})});
    els.newText.value = '';
    renderTodos([item, ...currentTodos]);
  } catch (e){ showToast('Add failed'); console.error(e); }
});

let currentTodos = [];
function renderTodos(items){
  currentTodos = items;
  els.list.innerHTML = items.map(t => `
    <li class="item ${t.done ? 'done':''}" data-id="${t.id}">
      <input type="checkbox" class="toggle" ${t.done ? 'checked':''} title="Mark done">
      <span class="text">${escapeHtml(t.text)}</span>
      <button class="delete">Delete</button>
    </li>`).join('');
}

els.list.addEventListener('click', async (e)=>{
  const li = e.target.closest('li.item');
  if (!li) return;
  const id = li.dataset.id;
  if (e.target.classList.contains('toggle')){
    try {
      const updated = await api(`/todos/${id}`, {method:'PATCH', body: JSON.stringify({done: e.target.checked})});
      renderTodos(currentTodos.map(x=> x.id===id ? updated : x));
    } catch(e){ showToast('Update failed'); console.error(e); }
  } else if (e.target.classList.contains('delete')){
    try {
      await api(`/todos/${id}`, {method:'DELETE'});
      renderTodos(currentTodos.filter(x=> x.id!==id));
    } catch(e){ showToast('Delete failed'); console.error(e); }
  }
});

async function loadTodos(){
  try {
    const items = await api('/todos');
    renderTodos(items);
  } catch(e){ showToast('Failed to load todos'); console.error(e); }
}

function escapeHtml(s){
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Init
updateView();
