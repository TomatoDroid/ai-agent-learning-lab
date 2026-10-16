/* 模块 3 的动画：记忆格式、记忆更新、BM25、混合检索、摘要索引、上下文感知检索、Agentic RAG */
(function () {
  const { define, h, syncList, esc } = window.Anim;

  function renderMessages(box, msgs) {
    syncList(box, msgs, m => m.k, () => h('div', { class: 'msg' }), (el, m) => {
      el.className = `msg ${m.role}${m.cls ? ' ' + m.cls : ''}`;
      el.innerHTML = `<span class="role">${esc(m.role)}</span>${m.html}`;
    });
  }
  const code = s => `<pre style="margin:0;font:12.5px/1.5 ui-monospace,monospace;white-space:pre-wrap;word-break:break-word">${s}</pre>`;

  // ───────────────────────── 3.1 四种存储格式 ─────────────────────────
  const CONV = [
    { k: 'u1', role: 'user', html: '帮我订下周五去东京的机票，我要<b>靠窗</b>，我<b>吃素</b>。' },
    { k: 'a1', role: 'assistant', html: '找到 3 个航班……ANA 直飞可以吗？', drop: true },
    { k: 'u2', role: 'user', html: '可以，用我的 MileagePlus <b>12345678</b>。另外帮我约<b>张医生</b>给我爸复查心脏。' },
  ];
  const FORMATS = [
    { name: 'Simple Notes', html: code('用户偏好靠窗座位\n用户吃素\n用户 MileagePlus：12345678\n张医生：心脏科'), pro: '开销极低，适合大量非关键事实', con: '信息被拆碎：“张医生”是谁的医生？丢了。' },
    { name: 'Enhanced Notes', html: code('用户订了下周五去东京的 ANA 直飞，偏好靠窗、吃素，\n用 MileagePlus 12345678 累积里程。用户请张医生\n为父亲复查心脏。'), pro: '保留叙事和语义完整', con: '冗余；一个属性变了要改好几段' },
    { name: 'JSON Cards', html: code('travel.seat = window\ntravel.meal = vegetarian\nloyalty.united = 12345678\nhealth.doctor = 张医生（心脏科）'), pro: '可部分更新、可预测', con: '刚性分类；还是分不清“为谁”' },
    { name: 'Advanced JSON Cards', html: code('{ key: doctor, value: 张医生（心脏科）,\n  <b>person: 父亲, relationship: father,</b>\n  <b>backstory: 用户为父亲约复查</b>, ts: 2025-01-03 }\n{ key: seat, value: window, person: user, … }'), pro: '“为谁”“为什么”“何时”都在：能消歧', con: '生成和维护更贵' },
  ];
  define('memory-formats', {
    title: '同一段对话，四种记法',
    ms: 3400,
    steps: [
      { show: 'conv', caption: '一段普通的订票对话。会话结束后，Harness 用<b>一次额外的 LLM 调用</b>提炼记忆。' },
      { show: 'extract', caption: '提炼三原则：<b>选择性</b>（“找到 3 个航班”是短期细节，丢掉）、<b>抽象化</b>（这次要靠窗 → 长期偏好）、<b>结构化</b>（可检索的字段）。' },
      { show: 0, caption: '<b>Simple Notes</b>：每条一个最小事实。便宜，但关联断了。' },
      { show: 1, caption: '<b>Enhanced Notes</b>：整段话保留上下文，语义完整，但难以局部更新。' },
      { show: 2, caption: '<b>JSON Cards</b>：类别 → 子类别 → 键值，可以只改一个字段。' },
      { show: 3, caption: '<b>Advanced JSON Cards</b>：加上 person、relationship、backstory、时间戳。下次用户说“帮我约张医生”，Agent 知道这位张医生是<b>父亲</b>的心脏科医生，而不是用户自己的牙医。' },
      { show: 'mix', caption: '实践中混合使用：<b>关键且少量</b>的（偏好、人物关系）用 Advanced JSON Cards，<b>大量且非关键</b>的用 Simple Notes。' },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="mf-conv"></div><div class="mf-body" style="margin-top:10px"></div>';
      return {
        render(s) {
          const extracting = s.show !== 'conv';
          renderMessages(stage.querySelector('.mf-conv'), CONV.map(m => ({ ...m, cls: extracting && m.drop ? 'dim' : '' })));
          const body = stage.querySelector('.mf-body');
          if (s.show === 'conv') body.innerHTML = '';
          else if (s.show === 'extract') body.innerHTML = `<div class="panel enter"><h4>提炼出的候选记忆</h4>${code('· 偏好靠窗座位（偏好）\n· 素食，飞机上要特殊餐（饮食限制）\n· United MileagePlus 12345678（会员）\n· 父亲的心脏科医生：张医生（人物关系）\n<s style="opacity:.5">· 搜索返回 3 个航班</s>')}</div>`;
          else if (s.show === 'mix') body.innerHTML = `<div class="grid2 enter"><div class="panel"><h4>关键且少量 → Advanced JSON Cards</h4>人物关系、长期偏好、证件信息</div><div class="panel"><h4>大量且非关键 → Simple Notes</h4>聊过的话题、一次性请求</div></div>`;
          else {
            const f = FORMATS[s.show];
            body.innerHTML = `<div class="panel enter"><h4>${f.name}</h4>${f.html}<div class="legend"><span class="pill ok">${esc(f.pro)}</span><span class="pill ${s.show === 3 ? 'warn' : 'bad'}">${esc(f.con)}</span></div></div>`;
          }
        },
      };
    },
  });

  // ───────────────────────── 3.1 写入时消歧 vs 只追加 ─────────────────────────
  function memSteps(mode) {
    const s1 = { k: 'm1', text: 'home_city = 北京', ts: '01-03' };
    const v2Bad = { k: 'm1', text: 'home_city = 上海', ts: '03-10', cls: 'bad' };
    const v3New = { k: 'm2', text: 'home_city = 上海', ts: '03-10', note: 'backstory：这三个月在上海出差' };
    const say1 = '会话 1：“我住在北京。”';
    const say2 = '会话 2：“这三个月我在上海出差，资料寄酒店。”';
    const ask = '会话 3：“把体检报告寄到我家。”';
    if (mode === 'v2') return [
      { say: say1, mem: [s1], caption: '提取事实，写入记忆。' },
      { say: say2, mem: [s1], op: 'LLM 判断：与“住在北京”冲突 → <b>UPDATE</b>', caption: 'Mem0 2025 年的做法：写入前检索相近记忆，由 LLM 在 ADD / UPDATE / DELETE / NOOP 中选一个。' },
      { say: say2, mem: [v2Bad], op: '“北京”被覆盖', caption: '这次判断错了：出差不是搬家。<b>旧值被覆盖，历史没了。</b>' },
      { say: ask, mem: [v2Bad], out: ['bad', '寄到上海'], caption: '错误的 UPDATE/DELETE 会<b>不可逆</b>地丢失信息，而且每条候选事实都要多一次检索和一次 LLM 判断。' },
    ];
    return [
      { say: say1, mem: [s1], caption: '同样提取并写入。' },
      { say: say2, mem: [s1, v3New], op: '<b>只做 ADD</b>，带上时间和背景', caption: 'Mem0 2026 年 v3 的做法：写入只追加，两条事实并存。' },
      { say: ask, mem: [s1, v3New], hl: true, caption: '冲突留到<b>检索时</b>处理：融合语义、关键词、实体匹配，并按时间排序；背景说明这是出差。' },
      { say: ask, mem: [s1, v3New], hl: true, out: ['good', '寄到北京的家；要不要同时寄一份到上海的酒店？'], caption: '历史还在，就还能纠正。Mem0 报告这一改动让 LoCoMo 从 71.4 升到 92.5。mini-agent 的 <code>MemoryStore</code> 也是只追加。' },
    ];
  }
  define('memory-update', {
    title: '记忆冲突：写入时覆盖，还是只追加？',
    ms: 3200,
    scenarios: [
      { id: 'v2', label: '写入时消歧（UPDATE）', steps: memSteps('v2') },
      { id: 'v3', label: '只追加（ADD）', steps: memSteps('v3') },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="mu-say msg user"></div><div class="mu-op muted" style="font-size:13px;margin:6px 0"></div><div class="panel"><h4>长期记忆</h4><div class="mu-mem"></div></div><div class="mu-out" style="margin-top:8px"></div>';
      return {
        render(s, i, sc) {
          stage.querySelector('.mu-say').innerHTML = `<span class="role">user</span>${esc(s.say)}`;
          stage.querySelector('.mu-op').innerHTML = s.op || '';
          syncList(stage.querySelector('.mu-mem'), s.mem, m => sc.id + m.k + m.text, () => h('div', { class: 'msg tool enter' }), (el, m) => {
            el.className = `msg tool${m.cls ? ' ' + m.cls : ''}${s.hl ? ' good' : ''}`;
            el.innerHTML = `<code>${esc(m.text)}</code> <span class="muted" style="font-size:12px">[${m.ts}]${m.note ? ' ' + esc(m.note) : ''}</span>`;
          });
          stage.querySelector('.mu-out').innerHTML = s.out ? `<span class="pill ${s.out[0] === 'good' ? 'ok' : 'bad'} enter">Agent：${esc(s.out[1])}</span>` : '';
        },
      };
    },
  });

  // ───────────────────────── 3.2 BM25 ─────────────────────────
  // 原书实验 3-5 的日志：N=10，k1=1.5，b=0.75，avgdl=250
  const K1 = 1.5, B = 0.75, AVG = 250;
  const sat = (tf, dl) => tf * (K1 + 1) / (tf + K1 * (1 - B + B * dl / AVG));
  const TERMS = [
    { t: '模型', df: 3, idf: 0.76, hits: [['doc_1', 5, 200], ['doc_3', 2, 500], ['doc_7', 8, 150]] },
    { t: '蒸馏', df: 2, idf: 1.22, hits: [['doc_1', 3, 200], ['doc_5', 1, 250]] },
  ];
  const DOCS = ['doc_1', 'doc_3', 'doc_5', 'doc_7'];
  function bmScores(upto) {
    const sc = {};
    TERMS.slice(0, upto).forEach(T => T.hits.forEach(([d, tf, dl]) => { (sc[d] = sc[d] || []).push({ t: T.t, v: T.idf * sat(tf, dl), tf, dl }); }));
    return sc;
  }
  define('bm25', {
    title: 'BM25：稀有词更重要，重复有上限',
    ms: 3600,
    steps: [
      { phase: 'q', caption: '查询“模型蒸馏”先分词：["模型", "蒸馏"]。在<b>倒排索引</b>里，每个词直接指向含有它的文档，不用扫描全部文档。（原书实验 3-5 的日志：10 篇文档，k1=1.5，b=0.75，平均长度 250 词）' },
      { phase: 'term', upto: 1, caption: '“模型”出现在 3 篇文档里，IDF = ln((10−3+0.5)/(3+0.5)) = 0.76。doc_7 出现 8 次又最短，贡献最大；doc_3 很长，同样出现 2 次也要打折。' },
      { phase: 'term', upto: 2, caption: '“蒸馏”只在 2 篇里出现，更稀有，IDF = 1.22。doc_1 里它只出现 3 次（比“模型”的 5 次少），贡献反而更大：2.15 &gt; 1.52。' },
      { phase: 'rank', upto: 2, caption: '把每个词的贡献加起来排序：doc_1 同时命中两个词，3.67 遥遥领先。' },
      { phase: 'sat', caption: '<b>词频饱和</b>：出现 10 次的贡献远不到出现 5 次的两倍（k1 控制饱和速度）。朴素 TF-IDF 是直线，BM25 是逐渐变平的曲线；长文档（b 控制）还要再打折。' },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="bm-q" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px"></div><div class="bm-body"></div>';
      return {
        render(s) {
          stage.querySelector('.bm-q').innerHTML = TERMS.map((T, j) =>
            `<div class="node ${s.upto > j || s.phase === 'q' ? 'on' : ''}" style="min-width:110px">${T.t}${s.phase !== 'q' && s.phase !== 'sat' ? `<div style="font-size:11px">df=${T.df} · IDF=${T.idf}</div>` : `<div class="muted" style="font-size:11px">→ ${T.hits.map(x => x[0]).join(', ')}</div>`}</div>`).join('');
          const body = stage.querySelector('.bm-body');
          if (s.phase === 'q') { body.innerHTML = ''; return; }
          if (s.phase === 'sat') {
            const W = 300, H = 120, xs = [...Array(11).keys()];
            const lin = x => x, bm = x => sat(x, 250) / sat(1, 250);  // 都以 tf=1 时的贡献为 1
            const pt = (f, x) => `${20 + x * 26},${H - 10 - f(x) * ((H - 20) / 10)}`;
            body.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:420px" role="img" aria-label="词频饱和曲线">
              <line x1="20" y1="${H - 10}" x2="${W - 10}" y2="${H - 10}" stroke="currentColor" opacity=".3"/>
              <polyline fill="none" stroke="var(--muted)" stroke-dasharray="4 3" stroke-width="2" points="${xs.map(x => pt(lin, x)).join(' ')}"/>
              <polyline fill="none" stroke="var(--accent)" stroke-width="2.5" points="${xs.map(x => pt(bm, x)).join(' ')}"/>
              <text x="40" y="16" font-size="10" fill="var(--muted)">TF-IDF：直线</text>
              <text x="${W - 70}" y="${H - 34}" font-size="10" fill="var(--accent)">BM25：饱和</text>
              <text x="${W - 30}" y="${H - 1}" font-size="10" fill="var(--muted)">TF</text></svg>
              <p class="muted" style="font-size:12.5px">示意：同一篇平均长度的文档，词频从 0 到 10。BM25 中 tf=10 的贡献只有 tf=5 的 ${(sat(10, 250) / sat(5, 250)).toFixed(2)} 倍。</p>`;
            return;
          }
          const sc = bmScores(s.upto);
          const rows = (s.phase === 'rank' ? DOCS.slice().sort((a, b) => sum(sc[b]) - sum(sc[a])) : DOCS).filter(d => sc[d]);
          function sum(arr) { return (arr || []).reduce((a, x) => a + x.v, 0); }
          const max = 3.8;
          body.innerHTML = rows.map(d => `<div style="display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px">
            <span style="width:48px">${d}</span>
            <div class="bar" style="flex:1;height:18px">${sc[d].map(x => `<span title="${x.t}" style="width:${x.v / max * 100}%;background:${x.t === '模型' ? 'var(--c-tool)' : 'var(--accent)'};border-right:2px solid var(--surface)"></span>`).join('')}</div>
            <span style="width:150px;font-variant-numeric:tabular-nums">${sc[d].map(x => `${x.t} ${x.v.toFixed(2)}`).join(' + ')}${s.phase === 'rank' ? ` = <b>${sum(sc[d]).toFixed(2)}</b>` : ''}</span></div>`).join('') +
            `<div class="legend"><span><i style="background:var(--c-tool)"></i>“模型”的贡献</span><span><i style="background:var(--accent)"></i>“蒸馏”的贡献</span></div>`;
        },
      };
    },
  });

  // ───────────────────────── 3.2 混合检索 ─────────────────────────
  const HDOC = { cat: 'Cat care guide', dog: 'Dog training basics', e403: 'HTTP-403 Forbidden：权限不足', e500: '服务器错误的通用排查' };
  function hySteps(q, dense, sparse, rerank, notes) {
    const fused = {};
    [dense, sparse].forEach(run => run.forEach((d, r) => { fused[d] = (fused[d] || 0) + 1 / (60 + r + 1); }));
    const fusedList = Object.keys(fused).sort((a, b) => fused[b] - fused[a]).map(d => ({ d, s: fused[d] }));
    return [
      { q, dense, sparse: null, caption: notes[0] },
      { q, dense, sparse, caption: notes[1] },
      { q, dense, sparse, fused: fusedList, caption: notes[2] },
      { q, dense, sparse, fused: fusedList, rerank, caption: notes[3] },
    ];
  }
  define('hybrid', {
    title: '混合检索：两路各有盲区，融合后都能找到',
    ms: 3400,
    scenarios: [
      {
        id: 'kitty', label: '查 “kitty”', steps: hySteps('kitty', ['cat', 'dog'], [], ['cat'], [
          '<b>稠密检索</b>懂语义：kitty 和 cat 在向量空间里挨得很近。',
          '<b>稀疏检索</b>只认字面：没有一篇文档写着 kitty，一无所获。',
          '<b>RRF 融合</b>只看名次：得分 = Σ 1/(60 + 名次)。一路没找到不扣分，另一路的结果照样保留。',
          '<b>重排序</b>：跨编码器把查询和候选拼在一起逐字比对，精排前 N 个。慢，但只用在少量候选上。',
        ]),
      },
      {
        id: '403', label: '查 “HTTP-403”', steps: hySteps('HTTP-403', ['e500', 'e403', 'dog'], ['e403'], ['e403', 'e500'], [
          '稠密检索只读出“这是个错误”，泛泛的“服务器错误”排在最前。',
          '稀疏检索精确匹配到 HTTP-403 这个代码。人名、型号、错误码都是稀疏检索的强项。',
          'HTTP-403 文档在两路都有名次，融合后超过“服务器错误”：1/62 + 1/61 &gt; 1/61。余弦（0～1）和 BM25（0～几十）尺度不同，只看名次就不用对齐分数。',
          '重排序后 HTTP-403 文档稳居第一。书中结论：<b>没有哪种单一检索在所有场景下都可靠。</b>',
        ]),
      },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="hy-q" style="margin-bottom:8px"></div><div class="hy-cols" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px"></div>';
      const col = (title, list, extra) => `<div class="panel"><h4>${title}</h4>${list === null ? '<p class="muted" style="font-size:12px">…</p>' : list.length ? list.map((x, r) => `<div class="msg tool enter" style="font-size:12.5px">${r + 1}. ${esc(HDOC[x.d || x])}${extra ? extra(x, r) : ''}</div>`).join('') : '<p class="muted enter" style="font-size:12.5px">（无结果）</p>'}</div>`;
      return {
        render(s) {
          stage.querySelector('.hy-q').innerHTML = `<span class="pill acc">查询：${esc(s.q)}</span>`;
          stage.querySelector('.hy-cols').innerHTML =
            col('稠密（语义）', s.dense) + col('稀疏（BM25）', s.sparse) +
            (s.fused ? col('RRF 融合', s.fused, x => ` <span class="muted">${x.s.toFixed(4)}</span>`) : '') +
            (s.rerank ? col('重排序', s.rerank) : '');
        },
      };
    },
  });

  // ───────────────────────── 3.3 原始案例 vs 提炼摘要 ─────────────────────────
  // 100 个笼子：90 黑 10 白；top-k 只取回其中一部分
  const CATS = [...Array(100)].map((_, i) => (i % 10 === 7 ? 'w' : 'b'));
  const PICK = new Set([2, 5, 9, 13, 17, 21, 24, 27, 33, 38, 44, 47, 51, 60, 66, 72, 85, 90]); // 15 黑 + 3 白
  define('summary-index', {
    title: '把案例直接放进知识库，为什么不够？',
    ms: 3400,
    scenarios: [
      {
        id: 'raw', label: '只存原始案例', steps: [
          { grid: 'all', caption: '知识库里有 100 篇巡查记录，每篇一只猫：90 只黑猫、10 只白猫。' },
          { grid: 'pick', caption: '用户问：“黑猫白猫比例是多少？” 检索只取回 top-k 条，模型只看到 <b>15 只黑猫、3 只白猫</b>。' },
          { grid: 'pick', out: ['bad', '“大约 83% 是黑猫”'], caption: '基于不完整的样本，自信地给出错误答案。模型无从知道自己没看全。' },
          { grid: 'tickets', caption: '同一个问题的另一种形态：几百条客服工单，每条只记一个个案（退伍军人通过、医生通过、教师被拒）。护士来问能否享受优惠？' },
          { grid: 'tickets', out: ['bad', '“护士和医生相近，应该可以”'], caption: '最近邻偏置 + 边界缺失：“仅限……其他一律不适用”不存在于任何一条工单里，调大 k 也找不到。' },
        ],
      },
      {
        id: 'sum', label: '索引前先提炼', steps: [
          { grid: 'all', summary: '统计摘要：共 100 只猫，90 只黑猫（90%），10 只白猫（10%）。', caption: '索引阶段多花一次计算：通读全部记录，生成一条统计摘要，和原始记录一起索引。' },
          { grid: 'none', summary: '统计摘要：共 100 只猫，90 只黑猫（90%），10 只白猫（10%）。', hit: true, out: ['good', '“90% 是黑猫”'], caption: '一次检索就拿到结论。这和 2.4 课的状态栏是同一个道理：<b>把需要推理的结论提前算好，变成可检索的知识</b>。' },
          { grid: 'tickets', summary: '规则卡：Xfinity 优惠适用于现役与退伍军人、持证医护人员（含护士）；教师等其他职业不适用。', hit: true, out: ['good', '“可以，护士属于持证医护人员”'], caption: '把散落在个案里的边界，提炼成一张带全称和否定的规则卡。这就是 RAPTOR、GraphRAG 等结构化索引想做的事：<b>在索引阶段投入计算，提炼、抽象、结构化</b>。' },
        ],
      },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="si-grid" style="line-height:0"></div><div class="si-sum" style="margin-top:8px"></div><div class="si-out" style="margin-top:8px"></div>';
      return {
        render(s) {
          const g = stage.querySelector('.si-grid');
          if (s.grid === 'tickets') {
            g.style.lineHeight = '';
            g.innerHTML = ['退伍军人 John：通过', '医生 Sarah：拿到折扣', '教师 Mike：不符合条件', '现役军人 Lee：通过', '……几百条'].map((t, j) => `<span class="pill ${j === 1 && s.out && s.out[0] === 'bad' ? 'warn' : ''}" style="margin:3px">${t}</span>`).join('');
          } else {
            g.style.lineHeight = '0';
            g.innerHTML = CATS.map((c, j) => {
              const on = s.grid === 'all' || (s.grid === 'pick' && PICK.has(j));
              return `<span style="display:inline-block;width:14px;height:14px;margin:2px;border-radius:3px;border:1px solid var(--border);background:${c === 'b' ? 'var(--text)' : 'var(--surface)'};opacity:${on ? 1 : 0.12};transition:opacity .4s"></span>`;
            }).join('');
          }
          stage.querySelector('.si-sum').innerHTML = s.summary ? `<div class="msg status ${s.hit ? 'good' : ''} enter"><span class="role">摘要</span>${esc(s.summary)}</div>` : '';
          stage.querySelector('.si-out').innerHTML = s.out ? `<span class="pill ${s.out[0] === 'good' ? 'ok' : 'bad'} enter">模型：${esc(s.out[1])}</span>` : '';
        },
      };
    },
  });

  // ───────────────────────── 3.3 上下文感知检索 ─────────────────────────
  define('contextual-retrieval', {
    title: '上下文感知检索：给每个块补上“身份”',
    ms: 3400,
    steps: [
      { phase: 'doc', caption: '一份 ACME 公司 2025 年 Q2 财报，按段落切块。' },
      { phase: 'chunks', caption: '切开后，第二块变成了孤立的一句：<b>“该公司</b>第二季度收入增长了 3%。”哪家公司？哪一年？信息留在了块的外面。' },
      { phase: 'search0', caption: '查询“ACME 最近的收入增长”：BM25 找不到“ACME”，稠密向量也读不出“该公司”指谁。别家公司的类似句子反而排在前面。' },
      { phase: 'prefix', caption: '索引前，让 LLM 读<b>全文 + 这一块</b>，写一句背景，拼在块前面再索引。全文部分每次相同，可以命中 Prompt Cache（2.2 课），成本约每百万文档 token 1 美元。' },
      { phase: 'search1', caption: '前缀同时增强了两路检索：BM25 多了“ACME”“2025”可以精确匹配，向量也有了语义背景。Anthropic 报告：结合 BM25 检索失败率降低 49%，再加重排序降低 67%。' },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="cr-body"></div>';
      const doc = '<b>ACME 公司 2025 年第二季度财报</b>｜一、关键业绩指标 ……｜二、收入：该公司第二季度收入增长了 3%。｜三、研发投入保持稳定 ……';
      return {
        render(s) {
          const b = stage.querySelector('.cr-body');
          const chunk = s.phase === 'prefix' || s.phase === 'search1'
            ? '<span class="pill acc enter">[节选自 ACME 公司 2025 年 Q2 财报的“收入”章节]</span> 该公司第二季度收入增长了 3%。'
            : '该公司第二季度收入增长了 3%。';
          const results = s.phase === 'search0'
            ? [['BETA 公司收入增长 5%。', 'bad'], ['该公司第二季度收入增长了 3%。', '']]
            : s.phase === 'search1' ? [['[ACME 2025 Q2 财报] 该公司第二季度收入增长了 3%。', 'good'], ['BETA 公司收入增长 5%。', '']] : null;
          b.innerHTML = `<div class="panel"><h4>原始文档</h4><div style="font-size:13px">${doc}</div></div>` +
            (s.phase === 'doc' ? '' : `<div class="arrow-down">↓ 分块</div><div style="display:flex;flex-direction:column;gap:6px">
              <div class="msg tool" style="opacity:.6">一、关键业绩指标 ……</div>
              <div class="msg tool ${s.phase === 'chunks' ? 'hl' : ''}">${chunk}</div>
              <div class="msg tool" style="opacity:.6">三、研发投入保持稳定 ……</div></div>`) +
            (results ? `<div class="panel enter" style="margin-top:10px"><h4>查询：“ACME 最近的收入增长” → 检索结果</h4>${results.map((r, j) => `<div class="msg ${r[1] || 'tool'}" style="font-size:12.5px">${j + 1}. ${esc(r[0])}</div>`).join('')}</div>` : '');
        },
      };
    },
  });

  // ───────────────────────── 3.3 Agentic RAG ─────────────────────────
  const AR = {
    u: { role: 'user', html: '我需要为我的车预约服务。' },
    pipe: { role: 'status', html: '固定流程：用用户原话检索一次 → search("我需要为我的车预约服务")' },
    r1: { role: 'tool', html: '[call-03-12] 用户为<b>本田 Accord</b> 预约了周五的保养。用户提到家里还有一辆<b>特斯拉</b>。' },
    bad: { role: 'assistant', html: '好的，已为您的本田 Accord 安排保养。', cls: 'bad' },
    c1: { role: 'assistant', html: '<i>思考：先查用户的车和保养记录。</i><br>tool_calls：search_user_memory("车 保养 预约")' },
    t1: { role: 'assistant', html: '<i>思考：记录里提到还有一辆特斯拉，信息不完整，再查一次。</i><br>tool_calls：search_user_memory("特斯拉")' },
    r2: { role: 'tool', html: '[call-04-02] 用户咨询<b>特斯拉 Model 3</b> 的轮胎更换，尚未预约。' },
    good: { role: 'assistant', html: '你是指已预约周五保养的本田 Accord，还是尚未预约的特斯拉 Model 3？', cls: 'good' },
  };
  const arSeq = keys => keys.map(k => ({ k, ...AR[k] }));
  define('agentic-rag', {
    title: '非智能体化 RAG vs 智能体化 RAG',
    ms: 3200,
    scenarios: [
      {
        id: 'pipe', label: '固定流程（检索一次）', steps: [
          { m: ['u'], caption: '用户有两辆车，分别在不同的电话里聊过（原书实验 3-9 的第二层用例）。' },
          { m: ['u', 'pipe', 'r1'], caption: '传统 RAG：用原话检索一次，把结果塞进上下文。' },
          { m: ['u', 'pipe', 'r1', 'bad'], caption: '只有一次机会。模型拿到一辆车就回答了，另一辆被忽略。对简单问题这很高效；对需要多跳的问题，能力上限很低。' },
        ],
      },
      {
        id: 'agent', label: '检索是工具（ReAct）', steps: [
          { m: ['u'], caption: '同一个问题。这次检索是一个<b>工具</b>，模型自己决定搜什么、搜几次。' },
          { m: ['u', 'c1', 'r1'], caption: '第一次搜索只返回了本田的记录。' },
          { m: ['u', 'c1', 'r1', 't1', 'r2'], caption: '模型<b>评估</b>结果：发现还提到一辆特斯拉，于是换关键词再搜。' },
          { m: ['u', 'c1', 'r1', 't1', 'r2', 'good'], caption: '信息充分后才回答，并主动澄清。代价是多了几次调用和延迟。检索结果仍然是不可信数据，要包上来源标记（2.3 课）。' },
        ],
      },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="ar-msgs"></div>';
      return { render(s, i, sc) { renderMessages(stage.querySelector('.ar-msgs'), arSeq(s.m).map(m => ({ ...m, k: sc.id + m.k }))); } };
    },
  });
})();
