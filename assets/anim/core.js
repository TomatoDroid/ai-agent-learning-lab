/*
 * 课程动画播放器。
 *
 * 每个动画用 Anim.define(name, spec) 注册：
 *   spec.title      标题
 *   spec.scenarios  [{ id, label, steps: [{ caption, ...state }] }]；只有一个场景时不显示切换按钮
 *   spec.mount(stage, ctx) 构建舞台 DOM，返回 { render(step, index, scenario) }
 * render 必须是“从状态到画面”的纯映射：任意跳到第 n 步都能画对。
 * 课文里用 <div class="anim" data-anim="name"></div> 引用。
 */
(function () {
  const registry = {};
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v == null || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'html') el.innerHTML = v;
        else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
        else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? '' : v);
      }
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return el;
  }

  // 按 key 同步列表：已有元素原地更新，新元素带入场动画，多余元素移除。
  function syncList(container, items, key, create, update) {
    const existing = new Map();
    for (const child of [...container.children]) existing.set(child.dataset.key, child);
    const seen = new Set();
    let prev = null;
    items.forEach((item, i) => {
      const k = String(key(item, i));
      seen.add(k);
      let el = existing.get(k);
      if (!el) {
        el = create(item, i);
        el.dataset.key = k;
        el.classList.add('enter');
      }
      if (update) update(el, item, i);
      const anchor = prev ? prev.nextSibling : container.firstChild;
      if (el !== anchor) container.insertBefore(el, anchor);
      prev = el;
    });
    for (const [k, el] of existing) if (!seen.has(k)) el.remove();
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function define(name, spec) { registry[name] = spec; }

  function mountAll(root) {
    root.querySelectorAll('.anim[data-anim]').forEach(el => {
      if (el.dataset.mounted) return;
      const spec = registry[el.dataset.anim];
      if (!spec) {
        el.innerHTML = '';
        el.append(h('div', { class: 'anim-fallback' }, `（动画 “${el.dataset.anim}” 尚未实现）`));
        return;
      }
      el.dataset.mounted = '1';
      try { new Player(el, spec); } catch (err) {
        console.error(err);
        el.innerHTML = '';
        el.append(h('div', { class: 'anim-fallback' }, '动画加载失败：' + err.message));
      }
    });
  }

  class Player {
    constructor(el, spec) {
      this.spec = spec;
      this.scenarios = spec.scenarios || [{ id: 'main', label: '', steps: spec.steps }];
      this.si = 0;
      this.i = 0;
      this.timer = null;
      el.innerHTML = '';
      el.setAttribute('role', 'region');
      el.setAttribute('aria-label', '动画：' + spec.title);

      const head = h('div', { class: 'anim-head' }, h('span', { class: 'anim-title' }, '▶ ' + spec.title));
      if (this.scenarios.length > 1) {
        this.tabs = this.scenarios.map((s, idx) => h('button', {
          class: 'anim-tab', type: 'button', 'aria-pressed': String(idx === 0),
          onclick: () => this.setScenario(idx),
        }, s.label));
        head.append(h('div', { class: 'anim-tabs' }, this.tabs));
      }
      this.stage = h('div', { class: 'anim-stage' });
      this.caption = h('div', { class: 'anim-caption', 'aria-live': 'polite' });
      this.btnFirst = h('button', { type: 'button', title: '回到开头', 'aria-label': '回到开头', onclick: () => { this.stop(); this.go(0); } }, '⏮');
      this.btnPrev = h('button', { type: 'button', title: '上一步', 'aria-label': '上一步', onclick: () => { this.stop(); this.go(this.i - 1); } }, '◀');
      this.btnPlay = h('button', { type: 'button', class: 'play', onclick: () => this.toggle() }, '播放');
      this.btnNext = h('button', { type: 'button', title: '下一步', 'aria-label': '下一步', onclick: () => { this.stop(); this.go(this.i + 1); } }, '▶');
      this.dots = h('div', { class: 'anim-dots' });
      const controls = h('div', { class: 'anim-controls' }, this.btnFirst, this.btnPrev, this.btnPlay, this.btnNext, this.counter = h('span', { class: 'muted', style: { fontSize: '12px', marginLeft: '6px' } }), this.dots);
      el.append(head, this.stage, this.caption, controls);

      this.view = spec.mount(this.stage, { h, syncList, esc });
      this.setScenario(0);
    }
    get steps() { return this.scenarios[this.si].steps; }
    setScenario(idx) {
      this.stop();
      this.si = idx;
      if (this.tabs) this.tabs.forEach((t, j) => t.setAttribute('aria-pressed', String(j === idx)));
      this.dots.innerHTML = '';
      this.steps.forEach((_, j) => this.dots.append(h('button', { type: 'button', 'aria-label': `第 ${j + 1} 步`, onclick: () => { this.stop(); this.go(j); } })));
      if (this.view.reset) this.view.reset(this.scenarios[idx]);
      this.go(0, true);
    }
    go(n, force) {
      const max = this.steps.length - 1;
      n = Math.max(0, Math.min(max, n));
      if (n === this.i && !force) return;
      this.i = n;
      const step = this.steps[n];
      this.view.render(step, n, this.scenarios[this.si]);
      this.caption.innerHTML = step.caption || '';
      this.counter.textContent = `${n + 1} / ${max + 1}`;
      [...this.dots.children].forEach((d, j) => d.classList.toggle('on', j <= n));
      this.btnFirst.disabled = this.btnPrev.disabled = n === 0;
      this.btnNext.disabled = n === max;
      if (n === max && this.timer) this.stop();
    }
    toggle() { this.timer ? this.stop() : this.play(); }
    play() {
      if (this.i === this.steps.length - 1) this.go(0);
      this.btnPlay.textContent = '暂停';
      const tick = () => {
        const ms = (this.steps[this.i].ms || this.spec.ms || 2800) * (reduceMotion ? 1.3 : 1);
        this.timer = setTimeout(() => {
          if (this.i >= this.steps.length - 1) return this.stop();
          this.go(this.i + 1);
          if (this.timer) tick();
        }, ms);
      };
      tick();
    }
    stop() {
      clearTimeout(this.timer);
      this.timer = null;
      this.btnPlay.textContent = '播放';
    }
  }

  window.Anim = { define, mountAll, h, syncList, esc };
})();
