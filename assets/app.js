(function () {
  const REPO = 'https://github.com/TomatoDroid/ai-agent-learning-lab';
  const BRANCH = 'codex/publish';
  const STORE_KEY = 'agent-course:v2';

  const $ = sel => document.querySelector(sel);
  const lessonEl = $('#lesson');
  const footerEl = $('#lesson-footer');
  const sidebar = $('#sidebar');

  let manifest = null;
  const byRoute = new Map();   // '#/l/1.2' -> entry
  const byPath = new Map();    // 'course/01-intro/1.2-react.md' -> entry
  const order = [];            // 线性顺序，用于上一课/下一课

  // ── 本地进度（读写都可能失败，失败时只是不记住） ──
  function loadState() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || { done: {} }; } catch { return { done: {} }; }
  }
  function saveState() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch { /* 隐私模式等 */ }
  }
  const state = loadState();

  function applyTheme(t) {
    if (t) document.documentElement.setAttribute('data-theme', t);
    else document.documentElement.removeAttribute('data-theme');
  }
  applyTheme(state.theme);
  $('#theme-toggle').addEventListener('click', () => {
    const dark = state.theme ? state.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    state.theme = dark ? 'light' : 'dark';
    applyTheme(state.theme);
    saveState();
  });
  $('#nav-toggle').addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    $('#nav-toggle').setAttribute('aria-expanded', String(open));
  });

  function resolvePath(base, rel) {
    const parts = base.split('/').slice(0, -1);
    for (const seg of rel.split('/')) {
      if (seg === '..') parts.pop();
      else if (seg && seg !== '.') parts.push(seg);
    }
    return parts.join('/');
  }

  async function init() {
    try {
      const res = await fetch('course/manifest.json', { cache: 'no-cache' });
      manifest = await res.json();
    } catch (err) {
      lessonEl.innerHTML = '<p>无法加载课程目录。请通过 HTTP 服务器打开本站（见 README 的“本地运行”）。</p>';
      return;
    }
    const home = { route: '#/', file: manifest.home, title: '课程首页', kind: 'home' };
    byRoute.set(home.route, home); byPath.set(home.file, home); order.push(home);
    for (const m of manifest.modules) {
      const mod = { route: `#/m/${m.id}`, file: m.page, title: m.title, kind: 'module', module: m };
      byRoute.set(mod.route, mod); byPath.set(mod.file, mod); order.push(mod);
      for (const l of m.lessons) {
        if (!l.file) continue;
        const e = { route: `#/l/${l.id}`, file: l.file, title: `${l.id} ${l.title}`, kind: 'lesson', lesson: l, module: m };
        byRoute.set(e.route, e); byPath.set(e.file, e); order.push(e);
      }
    }
    buildSidebar();
    window.addEventListener('hashchange', route);
    route();
  }

  function buildSidebar() {
    sidebar.innerHTML = '';
    const homeLink = document.createElement('a');
    homeLink.className = 'module-title'; homeLink.href = '#/'; homeLink.textContent = '课程首页';
    sidebar.append(homeLink);
    let part = null;
    for (const m of manifest.modules) {
      if (m.part !== part) {
        part = m.part;
        const h3 = document.createElement('h3'); h3.textContent = part; sidebar.append(h3);
      }
      const box = document.createElement('div'); box.className = 'module';
      const a = document.createElement('a'); a.className = 'module-title'; a.href = `#/m/${m.id}`; a.textContent = m.title;
      box.append(a);
      const ul = document.createElement('ul');
      for (const l of m.lessons) {
        const li = document.createElement('li');
        const link = document.createElement('a');
        link.href = l.file ? `#/l/${l.id}` : `#/m/${m.id}`;
        link.dataset.lesson = l.id;
        link.innerHTML = `<span class="dot"></span><span>${l.id} ${l.title}</span>` + (l.status === 'outline' ? '<span class="tag">大纲</span>' : '');
        li.append(link); ul.append(li);
      }
      box.append(ul); sidebar.append(box);
    }
    refreshProgress();
  }

  function refreshProgress() {
    const ready = manifest.modules.flatMap(m => m.lessons).filter(l => l.status === 'ready');
    const done = ready.filter(l => state.done[l.id]).length;
    $('#progress-pill').textContent = `${done} / ${ready.length} 课`;
    sidebar.querySelectorAll('a[data-lesson]').forEach(a => a.parentElement.classList.toggle('done', !!state.done[a.dataset.lesson]));
  }

  async function route() {
    const hash = location.hash || '#/';
    const entry = byRoute.get(hash) || byRoute.get('#/');
    sidebar.classList.remove('open');
    sidebar.querySelectorAll('a').forEach(a => a.classList.toggle('active', a.getAttribute('href') === entry.route));
    document.title = entry.kind === 'home' ? '深入理解 AI Agent · 实践课' : `${entry.title} · 深入理解 AI Agent`;
    lessonEl.innerHTML = '<p class="muted">加载中…</p>';
    let md;
    try {
      const res = await fetch(entry.file, { cache: 'no-cache' });
      if (!res.ok) throw new Error(res.status);
      md = await res.text();
    } catch (err) {
      lessonEl.innerHTML = `<p>无法加载 <code>${entry.file}</code>。</p>`;
      return;
    }
    lessonEl.innerHTML = marked.parse(md);
    rewriteLinks(entry.file);
    addHeadingIds();
    Anim.mountAll(lessonEl);
    renderFooter(entry);
    $('#main').focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  function rewriteLinks(base) {
    lessonEl.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href');
      if (/^(https?:|mailto:|#)/.test(href)) {
        if (/^https?:/.test(href)) { a.target = '_blank'; a.rel = 'noopener'; }
        return;
      }
      const [path, frag] = href.split('#');
      const full = resolvePath(base, path);
      const entry = byPath.get(full);
      if (entry) { a.href = entry.route; return; }
      const isFile = /\.[a-z0-9]+$/i.test(full);
      a.href = `${REPO}/${isFile ? 'blob' : 'tree'}/${BRANCH}/${full}${frag ? '#' + frag : ''}`;
      a.target = '_blank'; a.rel = 'noopener';
    });
    lessonEl.querySelectorAll('img[src]').forEach(img => {
      const src = img.getAttribute('src');
      if (!/^(https?:|data:)/.test(src)) img.src = resolvePath(base, src);
    });
  }

  function addHeadingIds() {
    lessonEl.querySelectorAll('h2, h3').forEach(hd => {
      if (!hd.id) hd.id = hd.textContent.trim().toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '');
    });
  }

  function renderFooter(entry) {
    footerEl.innerHTML = '';
    const idx = order.indexOf(entry);
    const prev = order[idx - 1];
    const next = order[idx + 1];
    const mk = (e, label) => {
      const a = document.createElement('a'); a.className = 'btn'; a.href = e.route; a.textContent = label + e.title; return a;
    };
    const left = document.createElement('div');
    if (prev) left.append(mk(prev, '← '));
    const mid = document.createElement('div');
    if (entry.kind === 'lesson' && entry.lesson.status === 'ready') {
      const id = entry.lesson.id;
      const btn = document.createElement('button'); btn.className = 'btn'; btn.type = 'button';
      const paint = () => {
        btn.classList.toggle('done', !!state.done[id]);
        btn.textContent = state.done[id] ? '✓ 已完成本课' : '标记本课为已完成';
      };
      btn.addEventListener('click', () => {
        if (state.done[id]) delete state.done[id]; else state.done[id] = new Date().toISOString().slice(0, 10);
        saveState(); paint(); refreshProgress();
      });
      paint(); mid.append(btn);
    }
    const right = document.createElement('div');
    if (next) { const b = mk(next, ''); b.textContent = next.title + ' →'; b.classList.add('primary'); right.append(b); }
    footerEl.append(left, mid, right);
  }

  init();
})();
