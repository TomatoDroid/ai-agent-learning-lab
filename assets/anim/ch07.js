/* 模块 7 的动画：任务解剖、Pass@k 与 Pass^k、分层验证与重置、Rubric 评判、配对比较与 Elo、失败归因、前缀回归、显著性、Harness 迭代、AB 测试 */
(function () {
  const { define, h, syncList, esc } = window.Anim;

  function renderMessages(box, msgs) {
    syncList(box, msgs, m => m.k, () => h('div', { class: 'msg' }), (el, m) => {
      el.className = `msg ${m.role}${m.cls ? ' ' + m.cls : ''}`;
      el.innerHTML = `<span class="role">${esc(m.label || m.role)}</span>${m.html}`;
    });
  }
  const pill = (cls, t) => `<span class="pill ${cls}">${t}</span>`;
  const nodeRow = (box, nodes, state) => syncList(box, nodes, n => n.id, () => h('div', { class: 'node', style: { flex: '1 1 90px', fontSize: '13px', padding: '6px 8px' } }), (el, n) => {
    el.className = `node ${state[n.id] || ''}`;
    el.innerHTML = n.name;
  });
  const FG = { on: 'var(--accent)', ok: 'var(--ok)', bad: 'var(--bad)', warn: 'var(--warn)', off: 'var(--muted)' };
  // 横向条形：rows=[{k,label,v(0..1),cls,text,lo,hi}]；lo/hi 画成区间
  function bars(box, rows) {
    syncList(box, rows, r => r.k, () => {
      const el = h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', margin: '5px 0' } });
      el.innerHTML = '<div class="b-l" style="flex:0 0 96px;font-size:12.5px;text-align:right;color:var(--muted)"></div><div class="b-t" style="position:relative;flex:1;height:18px;background:var(--surface-2);border-radius:5px;min-width:0"><div class="b-f" style="position:absolute;left:0;top:0;bottom:0;border-radius:5px;transition:width .5s ease,background .3s"></div><div class="b-ci" style="position:absolute;top:-3px;bottom:-3px;border:2px solid;border-radius:4px;transition:all .5s ease;box-sizing:border-box"></div></div><div class="b-v" style="flex:0 0 74px;font-size:12.5px;font-variant-numeric:tabular-nums"></div>';
      return el;
    }, (el, r) => {
      el.querySelector('.b-l').innerHTML = r.label;
      const f = el.querySelector('.b-f');
      f.style.width = (r.v * 100) + '%';
      f.style.background = FG[r.cls || 'on'];
      f.style.opacity = r.lo != null ? '.35' : '.85';
      const ci = el.querySelector('.b-ci');
      ci.style.display = r.lo != null ? '' : 'none';
      if (r.lo != null) { ci.style.left = (r.lo * 100) + '%'; ci.style.width = ((r.hi - r.lo) * 100) + '%'; ci.style.borderColor = FG[r.cls || 'on']; }
      el.querySelector('.b-v').innerHTML = r.text;
    });
  }
  const stats = (box, items) => { box.innerHTML = items.map(([k, v, cls]) => `<div class="stat"><div class="k">${k}</div><div class="v" style="${cls ? `color:${FG[cls]}` : ''}">${v}</div></div>`).join(''); };

  // ───────────────────────── 7.1 一条评估任务的解剖 ─────────────────────────
  const PARTS = [
    { id: 'ticket', name: '工单<div class="muted" style="font-size:11px">给 Agent</div>' },
    { id: 'user', name: '用户剧本<div class="muted" style="font-size:11px">known_info / 指令</div>' },
    { id: 'init', name: '初始状态<div class="muted" style="font-size:11px">两侧一起重置</div>' },
    { id: 'crit', name: '评分标准<div class="muted" style="font-size:11px">四层 + reward_basis</div>' },
  ];
  const LAYERS = [['env', 'env_assertions'], ['act', 'actions'], ['com', 'communicate_info'], ['nl', 'nl_assertions']];
  define('task-anatomy', {
    title: '解剖一条 τ²-bench telecom 任务',
    ms: 3600,
    scenarios: [
      { id: 'def', label: '任务定义', steps: [
        { on: 'ticket', m: ['t1'], caption: '工单只说症状：手机显示 No Service，客户在法国，测速必须达到 excellent 才算解决。<b>真正的病因不在工单里</b>。' },
        { on: 'user', m: ['t1', 't2'], caption: '用户模拟器的 <code>known_info</code> 只有姓名、号码和所在国家。飞行模式开着、漫游关着，用户自己也不知道：渐进式信息透露是<b>建模出来的</b>，不是靠一句“别一次说完”。' },
        { on: 'user', m: ['t1', 't2', 't3'], caption: '还有两条约束防止模拟器被 Agent “忽悠”：只认 excellent；回答设备状态必须以工具结果为准（事实锚定）。少了它，评估会退化成两个模型互相确认。' },
        { on: 'init', m: ['t1', 't2', 't3', 't4'], side: true, caption: '初始状态同时设置两侧：用户手机开飞行模式、关漫游；运营商数据库里漫游已开通。Agent 查数据库只会看到“配置正常”，<b>故障在它看不见的一侧</b>。' },
        { on: 'crit', m: ['t1', 't2', 't3', 't4'], side: true, layers: { env: 'acc', act: '', com: '', nl: '' }, caption: '评分标准有四层：终态断言、关键动作、必须告知的信息、自然语言断言。这条任务的 <code>reward_basis</code> 只有 ENV_ASSERTION：只按终态计分。' },
      ] },
      { id: 'pass', label: '一次满分运行', steps: [
        { on: 'ticket', m: ['r1', 'r2'], caption: '第 4 条消息：Agent 一次发出两个查询。政策第一句就写着 “You should only make one tool call at a time”。' },
        { on: 'user', m: ['r1', 'r2', 'r3'], caption: '第 17 条：只查了 L1001 就下结论“号码不在活跃线路中”。用户坚持，它才继续查到 L1002。' },
        { on: 'user', m: ['r1', 'r2', 'r3', 'r4'], side: true, caption: '第 30 条，转折点：<b>发出工具调用的是用户</b>。模拟用户有自己的工具（看状态栏、开关飞行模式、测速），这就是<b>双控</b>。' },
        { on: 'crit', m: ['r1', 'r2', 'r3', 'r4', 'r5'], side: true, fixed: true, layers: { env: 'ok', act: '', com: '', nl: '' }, reward: 1, caption: '关飞行模式、开漫游，测速 275 Mbps Excellent。两条终态断言通过，<code>reward = 1.0</code>。' },
        { on: 'crit', m: ['r1', 'r2', 'r3', 'r4', 'r5'], side: true, fixed: true, layers: { env: 'ok', act: 'warn', com: '', nl: '' }, reward: 1, caption: '第 4 条的违规没有被扣分，因为只按终态计分。这是二元奖励的固有代价：用过程颗粒度换跨模型可比的单一数字。生产评估还要指出<b>问题出在哪</b>（练习 7.1b）。' },
      ] },
      { id: 'fail', label: '那条失败的运行', steps: [
        { on: 'ticket', m: ['f1'], caption: '另一条任务：用户号码 555-123-2002，Agent 却选定了 L1001，并按它 3.2/5 GB 的用量往下推。' },
        { on: 'ticket', m: ['f1', 'f2'], caption: '<code>get_details_by_id(L1001)</code> 明确返回号码是 555-123-2001。<b>Agent 读到了，却没有修正判断</b>。' },
        { on: 'crit', m: ['f1', 'f2', 'f3'], layers: { env: 'bad', act: '', com: '', nl: '' }, reward: 0, caption: '之后几十条消息都在无关排查，最后转人工。省流模式确实关掉了，但该充的 2 GB 没充，三条终态断言全部失败，得 0 分。' },
        { on: 'crit', m: ['f1', 'f2', 'f3'], layers: { env: 'bad', act: '', com: '', nl: '' }, reward: 0, tally: true, caption: '五条任务过了四条。0.8 能不能用？退款客服意味着每五个用户就有一个拿不到退款；漏洞挖掘则五次中四次已很可观。<b>先定义什么算成功，数字才有意义</b>。' },
      ] },
    ],
    mount(stage) {
      const M = {
        t1: { k: 't1', role: 'system', label: 'ticket', html: '用户手机无法上网，状态栏显示 No Service。John Smith，555-123-2002，当前在法国。速度测试为 excellent 才算解决。' },
        t2: { k: 't2', role: 'user', label: 'known_info', html: 'You are John Smith with phone number 555-123-2002. You are currently abroad in France.' },
        t3: { k: 't3', role: 'user', label: 'task_instructions', html: '…only when speed test returns <b>excellent</b>… always ground your responses on the results of tool calls. Never make up the results of tool calls.' },
        t4: { k: 't4', role: 'tool', label: 'initial_state', html: 'user：turn_airplane_mode_on · turn_roaming_off<br>assistant：enable_roaming(C1001, L1002)' },
        r1: { k: 'r1', role: 'user', html: '我手机在法国上不了网。' },
        r2: { k: 'r2', role: 'assistant', label: 'assistant · 4', html: '→ <code>get_customer_by_phone</code> + <code>get_customer_by_name</code>（同时两个）', cls: 'bad' },
        r3: { k: 'r3', role: 'assistant', label: 'assistant · 17', html: '号码 555-123-2002 不在您的活跃线路中，最接近的是 555-123-2001……', cls: 'bad' },
        r4: { k: 'r4', role: 'user', label: 'user · 30–33', html: '→ <code>check_status_bar()</code><br>Airplane Mode: ON | no_service | Data Roaming: No<br>“我看到手机处于飞行模式……要我关掉试一下吗？”' },
        r5: { k: 'r5', role: 'tool', label: 'user tool · 46', html: '<code>run_speed_test()</code> → 275 Mbps, Excellent', cls: 'good' },
        f1: { k: 'f1', role: 'assistant', html: '您的线路 L1001 本月已用 3.2/5 GB……' },
        f2: { k: 'f2', role: 'tool', html: '<code>get_details_by_id(L1001)</code> → phone: 555-123-<b>2001</b>', cls: 'bad' },
        f3: { k: 'f3', role: 'assistant', html: '我为您转接人工客服。', cls: 'dim' },
      };
      stage.innerHTML = `<div class="ta-parts" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px"></div>
        <div class="ta-side"></div><div class="m-msgs"></div><div class="ta-v"></div>`;
      return {
        render(s) {
          nodeRow(stage.querySelector('.ta-parts'), PARTS, Object.fromEntries(PARTS.map(p => [p.id, p.id === s.on ? 'on' : ''])));
          stage.querySelector('.ta-side').innerHTML = !s.side ? '' : `<div class="grid2" style="margin-bottom:8px;gap:8px"><div class="panel"><h4>Agent 侧（运营商数据库）</h4>${pill('ok', '漫游已开通')} ${pill('', '线路 L1001/L1002/L1003')}</div><div class="panel"><h4>用户侧（手机）</h4>${s.fixed ? pill('ok', '飞行模式 关') + ' ' + pill('ok', '漫游 开') : pill('bad', '飞行模式 开') + ' ' + pill('bad', '漫游 关')}</div></div>`;
          renderMessages(stage.querySelector('.m-msgs'), s.m.map(k => M[k]));
          const L = s.layers;
          stage.querySelector('.ta-v').innerHTML = !L ? '' : `<div class="legend"><span>验证器：</span>${LAYERS.map(([id, n]) => pill(L[id] || '', (L[id] === 'ok' ? '✓ ' : L[id] === 'bad' ? '✗ ' : L[id] === 'warn' ? '! ' : '') + n + (id === 'env' ? '（计分）' : ''))).join('')}${s.reward != null ? pill(s.reward ? 'ok' : 'bad', `reward = ${s.reward}.0`) : ''}${s.tally ? pill('warn', '总计 4/5 = 0.8') : ''}</div>`;
        },
      };
    },
  });

  // ───────────────────────── 7.1 Pass@k 与 Pass^k ─────────────────────────
  const pk = (p, k) => [1 - Math.pow(1 - p, k), Math.pow(p, k)];
  // 固定的伪随机试验结果（p≈0.6），让圆点每次播放都一样
  const DRAWS = [1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1];
  define('pass-k', {
    title: 'Pass@k 看上限，Pass^k 看可靠',
    ms: 3000,
    scenarios: [
      { id: 'k', label: 'p = 0.6，k 增大', steps: [1, 2, 3, 4, 5].map(k => ({ p: 0.6, k, caption: [
        'k = 1：两个指标都等于单次成功率 60%。',
        'k = 2：至少成功一次的概率升到 84%；两次都成功只剩 36%。',
        'k = 3：93.6% 对 21.6%。同一个 Agent，两个指标开始讲完全不同的故事。',
        'k = 4：97.4% 对 13.0%。',
        'k = 5：<b>Pass@5 ≈ 99.0%，Pass^5 ≈ 7.8%</b>。前者适合衡量探索时的能力天花板（技术奇观），后者才接近退款、支付、权限变更的可靠性要求。',
      ][k - 1] })) },
      { id: 'p', label: 'k = 5，p 提高', steps: [
        { p: 0.6, k: 5, caption: '要让 Pass^5 变得可用，靠的不是多跑几次，而是把单次成功率本身做高。' },
        { p: 0.9, k: 5, caption: 'p = 0.9：Pass@5 早已饱和在 99.999%，Pass^5 也只有 59%。' },
        { p: 0.99, k: 5, caption: 'p = 0.99：Pass^5 ≈ 95%。“连续五次都不出错”对单次可靠性的要求有多苛刻，一目了然。' },
        { p: 0.99, k: 5, note: true, caption: '报告里要写清 k 次的口径：同一任务独立采样 k 次，还是流水线上连续 k 个任务。有副作用的操作不能“重试到成功为止”，要在沙盒或可回滚环境里采样，<b>每次失败都要记入可靠性</b>。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="pk-dots" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:6px;min-height:30px"></div><div class="pk-bars"></div><div class="pk-st stat-row"></div>';
      return {
        render(s) {
          const [at, hat] = pk(s.p, s.k);
          const draws = s.p === 0.6 ? DRAWS.slice(0, s.k) : Array.from({ length: s.k }, (_, i) => (s.p === 0.9 && i === 2) ? 0 : 1);
          stage.querySelector('.pk-dots').innerHTML = `<span class="muted" style="font-size:12.5px">同一任务跑 ${s.k} 次：</span>` + draws.map(d => `<span class="node ${d ? 'ok' : 'bad'}" style="padding:2px 8px;font-size:12px">${d ? '✓' : '✗'}</span>`).join('')
            + `<span class="muted" style="font-size:12px">（示意）Pass@k ${draws.some(Boolean) ? '✓' : '✗'} · Pass^k ${draws.every(Boolean) ? '✓' : '✗'}</span>`;
          bars(stage.querySelector('.pk-bars'), [
            { k: 'at', label: `Pass@${s.k}`, v: at, cls: 'on', text: (at * 100).toFixed(at > 0.999 ? 3 : 1) + '%' },
            { k: 'hat', label: `Pass^${s.k}`, v: hat, cls: hat < 0.5 ? 'bad' : hat < 0.9 ? 'warn' : 'ok', text: (hat * 100).toFixed(1) + '%' },
          ]);
          stats(stage.querySelector('.pk-st'), [['单次成功率 p', s.p], ['公式', '<span style="font-size:14px">1−(1−p)^k　·　p^k</span>']]);
        },
      };
    },
  });

  // ───────────────────────── 7.1 分层验证与每次重置 ─────────────────────────
  define('verify-layers', {
    title: '分层验证器与每次重置环境',
    ms: 3400,
    scenarios: [
      { id: 'basis', label: 'reward_basis', steps: [
        { calls: ['refund_order'], st: 'refunded', ans: '订单 A1001 已退款 59.0 元。', caption: '退款任务的成功定义：终态 <code>A1001.status == "refunded"</code>；动作 <code>get_order → refund_order</code>；回复里要有 A1001 和 59。这条轨迹没先查订单就直接退款了。' },
        { calls: ['refund_order'], st: 'refunded', ans: '订单 A1001 已退款 59.0 元。', checks: { ENV_ASSERTION: 1, ACTION: 0, COMMUNICATE: 1 }, basis: ['ENV_ASSERTION', 'COMMUNICATE'], caption: '<code>verify</code> 三层都算：环境 ✓、沟通 ✓、动作 ✗（缺少 get_order）。reward_basis 不含 ACTION，所以 <b>reward = 1.0</b>，但违规写进了 failures，没有被吞掉。' },
        { calls: ['refund_order'], st: 'refunded', ans: '订单 A1001 已退款 59.0 元。', checks: { ENV_ASSERTION: 1, ACTION: 0, COMMUNICATE: 1 }, basis: ['ENV_ASSERTION', 'ACTION', 'COMMUNICATE'], caption: '把 ACTION 加进 reward_basis，同一条轨迹就是 0 分。<b>算哪几层是评估设计者的选择</b>，要和业务风险对齐：涉及资金的操作，“先查再改”往往就是规则。' },
        { calls: ['get_order', 'refund_order'], st: 'refunded', ans: '已为你办理退款。', checks: { ENV_ASSERTION: 1, ACTION: 1, COMMUNICATE: 0 }, basis: ['ENV_ASSERTION', 'COMMUNICATE'], caption: '另一种失败：事做对了，话没说全，没说订单号和金额。原书统计 τ²-bench 基线里，有 80 次失败（占全部失败的三分之一）就是这样：<b>做对了但说错了</b>。' },
      ] },
      { id: 'reset', label: '不重置会怎样', steps: [
        { trial: 1, reset: true, calls: ['get_order', 'refund_order'], st: 'refunded', ans: '订单 A1001 已退款 59.0 元。', checks: { ENV_ASSERTION: 1, ACTION: 1, COMMUNICATE: 1 }, basis: ['ENV_ASSERTION', 'COMMUNICATE'], caption: '第 1 次试验：Agent 正常完成，环境里 A1001 变成 refunded。' },
        { trial: 2, reset: false, calls: [], st: 'refunded', ans: '订单 A1001 已退款 59.0 元。', checks: { ENV_ASSERTION: 1, ACTION: 0, COMMUNICATE: 1 }, basis: ['ENV_ASSERTION', 'COMMUNICATE'], caption: '第 2 次试验，<b>没有重置环境</b>：Agent 什么都没做，只嘴上说“已退款”。可上一次留下的 refunded 还在，终态断言照样通过。' },
        { trial: 2, reset: true, calls: [], st: 'delivered', ans: '订单 A1001 已退款 59.0 元。', checks: { ENV_ASSERTION: 0, ACTION: 0, COMMUNICATE: 1 }, basis: ['ENV_ASSERTION', 'COMMUNICATE'], caption: '每次从 <code>deepcopy(initial_state)</code> 重新开始、新建 Agent（练习 7.1c）：状态是 delivered，这次空口白话被判失败。环境可重置是五要素里“环境状态”的硬要求。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = `<div class="grid2" style="gap:8px"><div class="panel"><h4 class="vl-h">轨迹</h4><div class="vl-calls"></div><div class="vl-ans" style="margin-top:6px;font-size:13px"></div></div>
        <div class="panel"><h4>环境状态</h4><div class="vl-st"></div></div></div><div class="vl-checks" style="margin-top:8px"></div>`;
      return {
        render(s) {
          stage.querySelector('.vl-h').textContent = s.trial ? `第 ${s.trial} 次试验的轨迹` : '轨迹';
          stage.querySelector('.vl-calls').innerHTML = s.calls.length ? s.calls.map(c => pill('acc', '→ ' + c)).join(' ') : pill('', '（没有工具调用）');
          stage.querySelector('.vl-ans').innerHTML = `<span class="muted">回复：</span>${esc(s.ans)}`;
          stage.querySelector('.vl-st').innerHTML = `<code>orders.A1001.status</code><br>${pill(s.st === 'refunded' ? 'ok' : '', s.st)}${s.reset != null ? '<br>' + pill(s.reset ? 'acc' : 'warn', s.reset ? '已从初始状态重置' : '沿用上一次的状态') : ''}`;
          const c = s.checks;
          if (!c) { stage.querySelector('.vl-checks').innerHTML = ''; return; }
          const reward = s.basis.every(l => c[l]) ? 1 : 0;
          stage.querySelector('.vl-checks').innerHTML = `<div class="legend" style="margin:0">${Object.keys(c).map(l => pill(c[l] ? 'ok' : 'bad', `${c[l] ? '✓' : '✗'} ${l}${s.basis.includes(l) ? ' · 计分' : ''}`)).join('')}${pill(reward ? 'ok' : 'bad', `reward = ${reward}.0`)}</div>`;
        },
      };
    },
  });

  // ───────────────────────── 7.2 Rubric 评判 ─────────────────────────
  const DIMS = [['事实正确性', 'essential', 3], ['信息完整性', 'important', 2], ['思考正确性', 'important', 2]];
  const scoreOf = g => {
    if (g.veto) return 0;
    let n = 0, d = 0;
    DIMS.forEach(([name, , w], i) => { n += w * (g.g[i] - 1) / 3; d += w; });
    return n / d;
  };
  define('judge-pipeline', {
    title: 'Rubric 评判：分档、加权、一票否决',
    ms: 3600,
    scenarios: [
      { id: 'rubric', label: '三个回答', steps: [
        { a: 0, caption: '原书的例子：“我女儿的儿科医生是谁？”答案要跨两次对话关联：女儿叫 Lily；带 Lily 看了 Dr. Chen。Rubric 有三个分档维度和一个否决项。' },
        { a: 0, g: { g: [4, 3, 4] }, caption: '回答一准确且关联到了 Lily。评判模型逐项给档：4 / 3 / 4，幻觉检测 pass。必要项权重 3、重要项 2，按 (档位−1)/3 加权平均：<b>0.90</b>。' },
        { a: 1, g: { g: [4, 4, 4], veto: true }, caption: '回答二更长、更“周到”，三个维度都拿了满档，但它编造了就诊日期和诊断。<b>幻觉否决，总分归零</b>。原书 180 次评判里，否决触发了 28 次。' },
        { a: 2, g: { g: [3, 2, 3] }, caption: '回答三说对了医生，却把关系说含糊了：3 / 2 / 3，0.57。每一档都写成可验证的具体行为（“准确回答 Dr. Chen”），而不是“展示了深刻理解”，评判才稳定（练习 7.2a）。' },
      ] },
      { id: 'length', label: '长度偏差', steps: [
        { audit: 0, caption: '评判模型的典型偏见：<b>越长分越高</b>，哪怕内容并不更正确。下面是一次示意的审计：每个点是一个回答。' },
        { audit: 1, caption: '算评分和回答长度的相关系数：0.9。高分几乎总伴随长回答，说明评判被长度带偏了（示意数据）。' },
        { audit: 2, caption: '三种防范：Rubric 里显式惩罚冗长、规定长度上限；配对比较前把两个候选的长度控制到相近；<b>定期审计相关性</b>（<code>length_bias</code>）。修订 Rubric 后，相关性回落。' },
      ] },
    ],
    mount(stage) {
      const ANS = ['是 Dr. Chen，Lily 的儿科医生。', '是 Dr. Chen！你上次 3 月 12 日带 Lily 去复诊，诊断是轻度过敏，医生建议……（还写了三段）', '应该是 Dr. Chen 吧，好像是给孩子看病的那位。'];
      stage.innerHTML = '<div class="jp-a"></div><div class="jp-g"></div><div class="jp-st stat-row"></div>';
      return {
        render(s) {
          if (s.audit != null) {
            const pts = s.audit === 2 ? [[20, .5], [40, .8], [60, .45], [90, .6], [120, .9], [150, .35], [180, .7], [220, .55]] : [[20, .2], [40, .3], [60, .35], [90, .5], [120, .6], [150, .7], [180, .85], [220, .95]];
            stage.querySelector('.jp-a').innerHTML = `<svg viewBox="0 0 260 120" style="width:100%;max-width:420px;display:block;margin:auto"><line x1="20" y1="100" x2="250" y2="100" stroke="var(--border)"/><line x1="20" y1="10" x2="20" y2="100" stroke="var(--border)"/>
              <text x="250" y="114" font-size="9" text-anchor="end">回答长度 →</text><text x="24" y="16" font-size="9">评分</text>
              ${pts.map(([x, y]) => `<circle cx="${20 + x}" cy="${100 - y * 85}" r="4" fill="${s.audit === 2 ? 'var(--ok)' : 'var(--accent)'}" style="transition:all .5s"/>`).join('')}</svg>`;
            stage.querySelector('.jp-g').innerHTML = '';
            stats(stage.querySelector('.jp-st'), s.audit ? [['评分与长度的相关系数', s.audit === 2 ? '0.1' : '0.9', s.audit === 2 ? 'ok' : 'bad']] : [['审计对象', '<span style="font-size:14px">8 个回答（示意）</span>']]);
            return;
          }
          stage.querySelector('.jp-a').innerHTML = `<div class="msg user"><span class="role">问题</span>我女儿的儿科医生是谁？</div><div class="msg assistant enter${s.g && s.g.veto ? ' bad' : ''}"><span class="role">回答 ${s.a + 1}</span>${esc(ANS[s.a])}</div>`;
          const g = s.g;
          bars(stage.querySelector('.jp-g'), [
            ...DIMS.map(([n, w, wt], i) => ({ k: n, label: `${n}<br><span style="font-size:11px">${w} ×${wt}</span>`, v: g ? (g.g[i] - 1) / 3 : 0, cls: g && g.veto ? 'off' : 'on', text: g ? `${g.g[i]} 档` : '—' })),
            { k: 'veto', label: '幻觉检测<br><span style="font-size:11px">veto</span>', v: g ? 1 : 0, cls: g && g.veto ? 'bad' : 'ok', text: g ? (g.veto ? 'fail' : 'pass') : '—' },
          ]);
          const t = g ? scoreOf(g) : null;
          stats(stage.querySelector('.jp-st'), [['总分', t == null ? '—' : t.toFixed(2), t == null ? '' : t === 0 ? 'bad' : t > 0.8 ? 'ok' : 'warn'], ['公式', '<span style="font-size:13px">Σ w·(g−1)/3 ÷ Σ w；否决 → 0</span>']]);
        },
      };
    },
  });

  // ───────────────────────── 7.2 配对比较与 Elo ─────────────────────────
  const eloE = (a, b) => 1 / (1 + Math.pow(10, (b - a) / 400));
  define('pairwise-elo', {
    title: '配对比较：交换位置判两次，再用 Elo 排名',
    ms: 3400,
    scenarios: [
      { id: 'swap', label: '位置偏差', steps: [
        { j: [], caption: '不打绝对分，只问“甲和乙哪个更好”，往往更稳。但评判模型会<b>偏爱某个位置</b>（通常是第一个）。' },
        { j: [['甲', '乙', 'A']], caption: '第一次：甲放在“回答 A”，乙放在“回答 B”。评判说 A 更好，也就是甲。' },
        { j: [['甲', '乙', 'A'], ['乙', '甲', 'A']], verdict: 'tie', caption: '交换位置再判：乙在前。评判<b>又说 A</b>，这回 A 是乙。两次矛盾：它在跟着位置走，不是在看内容。记为平局（或送人工复核）。' },
        { j: [['甲', '乙', 'A'], ['乙', '甲', 'B']], verdict: 'a', caption: '如果第二次说 B（也就是甲），两次都指向甲，才算甲赢（练习 7.2b 的 <code>pairwise</code>）。Chatbot Arena 的做法本质相同：随机化展示位置。' },
      ] },
      { id: 'elo', label: 'Elo 更新', steps: [
        { r: [1200, 1000], caption: '模型 A 1200 分，B 1000 分。Elo 预测 A 的胜率：1 / (1 + 10^((1000−1200)/400)) ≈ <b>76%</b>。' },
        { r: [1207.7, 992.3], win: 'A', caption: 'A 赢了。意料之中，K=32 时 A 只涨 7.7 分，B 跌同样多。' },
        { r: [1175.7, 1024.3], win: 'B', caption: '换个结局：B 爆冷赢了。A 掉 24.3 分，B 涨同样多。<b>出乎意料的结果带来更大的调整</b>，排名因此能较快收敛。' },
        { r: [1175.7, 1024.3], win: 'B', note: true, caption: 'Elo 是 Bradley-Terry 模型的在线更新版，结果受 K 和<b>比赛顺序</b>影响。原书实验 7-8：在 180 万条 Arena 投票上，在线 Elo 和 BT 拟合的排名 Spearman 相关 0.787，Top-20 重合 12 个。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="pe-main"></div><div class="pe-st stat-row"></div>';
      return {
        render(s) {
          if (s.j) {
            stage.querySelector('.pe-main').innerHTML = s.j.map(([a, b, c], i) => `<div class="panel enter" style="margin:4px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap"><span class="muted" style="font-size:12px">第 ${i + 1} 次</span>
              <span class="node ${c === 'A' ? 'on' : ''}" style="padding:3px 10px;font-size:13px">回答 A：${a}</span><span class="node ${c === 'B' ? 'on' : ''}" style="padding:3px 10px;font-size:13px">回答 B：${b}</span>
              <span>→ 评判：${c}（${c === 'A' ? a : b}）</span></div>`).join('') || '<div class="panel muted">还没有开始判。</div>';
            stats(stage.querySelector('.pe-st'), [['结论', s.verdict ? (s.verdict === 'tie' ? '平局：位置偏差' : '甲赢') : '—', s.verdict === 'tie' ? 'warn' : s.verdict ? 'ok' : '']]);
            return;
          }
          const [ra, rb] = s.r;
          const e = eloE(1200, 1000);
          bars(stage.querySelector('.pe-main'), [
            { k: 'a', label: '模型 A', v: (ra - 800) / 600, cls: s.win === 'B' ? 'bad' : 'on', text: ra.toFixed(1) },
            { k: 'b', label: '模型 B', v: (rb - 800) / 600, cls: s.win === 'B' ? 'ok' : 'on', text: rb.toFixed(1) },
          ]);
          stats(stage.querySelector('.pe-st'), [['赛前 A 的期望胜率', (e * 100).toFixed(0) + '%'], ['本场', s.win ? `${s.win} 赢` : '—', s.win === 'B' ? 'warn' : ''], ['K', 32]]);
        },
      };
    },
  });

  // ───────────────────────── 7.2 失败归因 ─────────────────────────
  const STEPS_N = 32;
  define('failure-attribution', {
    title: '失败归因：找到第一个错误，再找根因',
    ms: 3600,
    scenarios: [
      { id: 'aw', label: 'AndroidWorld 记账', steps: [
        { marks: {}, caption: '任务：把图库里 <code>expenses.jpg</code> 的开销录入记账应用。Agent 用了 32 步：授权、搜索、打开图片、逐条填写、保存，<b>没有任何一步报错</b>，最后自己宣告完成。' },
        { marks: { 32: 'bad' }, caption: '验收：应写入的记录（Dress，¥436.35）不存在。最后一步只是结果，不能把最后一个错误当成根因。' },
        { marks: { 32: 'bad', 11: 'bad' }, after: 11, caption: '第 11 步：四条数据“Coffee $4.50、Lunch $12.75……”凭空出现。之后每一次输入和保存都基于这些编造的数据。' },
        { marks: { 32: 'bad', 11: 'bad', 8: 'warn' }, after: 8, quote: true, caption: '再往前，第 8 步的思考里写着：<i>I cannot actually see the content/details of the expenses in the image</i>。它知道自己没拿到数据，却既没停下也没报告。<b>第一个错误在第 8 步</b>，而它既不是报错，也不是工具调用。' },
        { marks: { 32: 'bad', 11: 'bad', 8: 'warn' }, after: 8, root: true, caption: '根因归属：T3A 是纯文本 Agent，观察空间里只有元素树，<b>根本没有图像像素</b>。根因不是“模型不会 OCR”，而是 Harness 的观察通道缺失。记错了，就会去换模型，而该做的是补通道。' },
      ] },
      { id: 'bisect', label: '二分定位', steps: [
        { probes: [], caption: '人工逐步读 32 步很贵。如果能“保留前 i 步、从第 i+1 步起换成正确做法”重放，就能问：<b>到第 i 步为止还救得回来吗？</b>' },
        { probes: [[16, 0]], caption: '试第 16 步：救不回来。第一个错误在 1–16 之间。' },
        { probes: [[16, 0], [8, 0]], caption: '试第 8 步：还是救不回来。范围缩到 1–8。' },
        { probes: [[16, 0], [8, 0], [4, 1]], caption: '试第 4 步：救得回来。范围是 5–8。' },
        { probes: [[16, 0], [8, 0], [4, 1], [6, 1], [7, 1]], found: 8, caption: '再试 6、7，都救得回来，所以第一个错误就是第 8 步。<b>5 次重放代替 32 次</b>（练习 7.2c 的 <code>first_error</code>）。前提是单调：一旦救不回来，之后也救不回来。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = `<div class="fa-steps" style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:8px"></div><div class="fa-info"></div>`;
      return {
        render(s) {
          const box = stage.querySelector('.fa-steps');
          const items = Array.from({ length: STEPS_N }, (_, i) => i + 1);
          const probe = Object.fromEntries((s.probes || []).map(([i, ok]) => [i, ok]));
          syncList(box, items, i => i, () => h('div', { class: 'node', style: { flex: '0 0 auto', width: '26px', padding: '3px 0', fontSize: '11px' } }), (el, i) => {
            let cls = '';
            if (s.marks) cls = s.marks[i] || (s.after && i > s.after && i < 32 ? 'off' : '');
            if (s.probes) cls = i in probe ? (probe[i] ? 'ok' : 'bad') : (s.found === i ? 'on' : '');
            if (s.found === i) cls = 'on';
            el.className = `node ${cls}`;
            el.textContent = i;
          });
          let info = '';
          if (s.quote) info += '<div class="msg assistant bad enter"><span class="role">第 8 步 · 思考</span>I cannot actually see the content/details of the expenses in the image…（继续推进）</div>';
          if (s.root) info += `<div class="legend enter">${pill('', '表面：模型不会 OCR')}${pill('bad', '✗ 换模型 / 做 OCR 训练')}${pill('ok', '根因：观察通道缺失 → 补通道')}</div>`;
          if (s.probes) info = `<div class="legend" style="margin:0">${pill('ok', '救得回来')}${pill('bad', '救不回来')}${s.found ? pill('acc', `第一个错误：第 ${s.found} 步`) : ''}<span>重放次数：${s.probes.length}</span></div>`;
          stage.querySelector('.fa-info').innerHTML = info;
        },
      };
    },
  });

  // ───────────────────────── 7.2 端到端回归与前缀回归 ─────────────────────────
  define('prefix-regression', {
    title: '轨迹前缀回归：冻结上下文，只看下一步',
    ms: 3400,
    scenarios: [
      { id: 'prefix', label: '可接受动作集合', steps: [
        { m: ['p1', 'p2'], caption: '端到端回归从头跑整个任务，最接近生产，却说不清坏在哪一步。前缀回归把首错之前的上下文<b>冻结下来</b>：系统提示、用户的话、已有的工具结果。' },
        { m: ['p1', 'p2'], allow: true, caption: '答案不是唯一的动作，而是<b>可接受动作集合</b>：先查订单状态，或者先问清楚，都可以；直接取消不行。' },
        { m: ['p1', 'p2'], allow: true, cand: [['→ get_order("A1003")', 'tool:get_order', 1], ['请问要取消的是哪一单？', 'ask', 1], ['→ cancel_order("A1003")', 'tool:cancel_order', 0], ['好的，已经帮你取消了。', 'say', 0]], caption: '每个用例只调一次模型，把回复翻译成动作标签再比对（练习 7.2c 的 <code>check_prefix</code>）。便宜、确定，不受前面步骤随机性的影响。' },
      ] },
      { id: 'repr', label: '实验 7-7', steps: [
        { r: null, caption: '原书实验 7-7：同一组用户记忆，用 JSON Cards、Markdown、Python-like 三种语义等价的写法给模型，跑 11 个前缀边界用例。' },
        { r: [6, 6, 6], caption: '三种表示的总成绩<b>碰巧都是 6/11</b>。只看总分，会以为表示方式无所谓。' },
        { r: [6, 6, 6], diff: true, caption: '但失败位置不同：Markdown 过了“仓库规则未知时先检查”，却多挂了一个作用域冲突；另两种相反。三种都没过：论文风格过度泛化、过时偏好覆盖当前要求、高风险删除前确认。<b>换表示不会自动修好应用策略</b>。' },
      ] },
    ],
    mount(stage) {
      const M = {
        p1: { k: 'p1', role: 'system', html: '已送达的订单不能取消，只能退款。修改订单前先查清状态。' },
        p2: { k: 'p2', role: 'user', html: '我是 lily，帮我取消订单 A1003。' },
      };
      stage.innerHTML = '<div class="m-msgs"></div><div class="pr-x"></div>';
      return {
        render(s) {
          if (s.m) {
            renderMessages(stage.querySelector('.m-msgs'), s.m.map(k => M[k]));
            let x = s.allow ? `<div class="legend enter"><span>可接受：</span>${pill('ok', 'tool:get_order')}${pill('ok', 'ask')}<span>其他都不行</span></div>` : '';
            if (s.cand) x += `<div style="margin-top:6px">${s.cand.map(([t, l, ok]) => `<div class="msg assistant ${ok ? 'good' : 'bad'} enter"><span class="role">候选 · ${l}</span>${esc(t)} ${pill(ok ? 'ok' : 'bad', ok ? '✓ 可接受' : '✗ 不在集合')}</div>`).join('')}</div>`;
            stage.querySelector('.pr-x').innerHTML = x;
            return;
          }
          stage.querySelector('.m-msgs').innerHTML = '';
          const names = ['JSON Cards', 'Markdown', 'Python-like'];
          const fail = [['作用域冲突 A', 0, 1, 0], ['先检查仓库规则', 1, 0, 1], ['论文风格泛化', 1, 1, 1], ['过时偏好覆盖', 1, 1, 1], ['删除前确认', 1, 1, 1]];
          stage.querySelector('.pr-x').innerHTML = !s.r ? `<div class="legend">${names.map(n => pill('acc', n)).join('')}<span>同一份记忆的三种写法</span></div>`
            : `<div class="stat-row">${names.map((n, i) => `<div class="stat"><div class="k">${n}</div><div class="v">${s.r[i]}/11</div></div>`).join('')}</div>`
              + (s.diff ? `<div class="panel enter" style="margin-top:8px"><h4>部分用例的失败分布（✗ = 失败）</h4><div style="display:grid;grid-template-columns:minmax(0,1.4fr) repeat(3,minmax(0,1fr));gap:4px;font-size:12.5px"><span></span>${names.map(n => `<b style="font-size:11.5px">${n}</b>`).join('')}${fail.map(([c, ...v]) => `<span>${c}</span>${v.map(x => `<span>${x ? pill('bad', '✗') : pill('ok', '✓')}</span>`).join('')}`).join('')}</div></div>` : '');
        },
      };
    },
  });

  // ───────────────────────── 7.3 统计显著性 ─────────────────────────
  define('significance', {
    title: '70% 对 73%：是进步还是噪声？',
    ms: 3600,
    scenarios: [
      { id: 'ci', label: '置信区间', steps: [
        { n: 100, ci: false, caption: '100 道题，旧模型 70%，新模型 73%。看起来新模型好 3 个点。' },
        { n: 100, ci: true, caption: '画出 95% 置信区间：SE = √(p(1−p)/n)，70% 时约 <b>±9 个点</b>。两个区间大面积重叠，“73 对 70”不足以支持切换。' },
        { n: 897, ci: true, caption: '想把区间压到 ±3 个点，需要约 897 道题（<code>n_for_margin(0.7, 0.03)</code>）。标准误按 1/√n 缩小：精度提高 3 倍，题量要乘 9。' },
      ] },
      { id: 'paired', label: '配对检验', steps: [
        { t: [70, 0, 3, 27], caption: '但两个版本跑的是<b>同一批题</b>，应当逐题配对。都对、都错的题不说明谁更好，只有“一个对、一个错”的不一致对有信息。' },
        { t: [70, 0, 3, 27], p: 0.25, caption: '情况一：B 多对了 3 道、没多错一道。3 比 0，像连抛三次硬币都是正面：McNemar 精确检验 p = 0.25，仍不显著。' },
        { t: [57, 13, 16, 14], p: 0.711, caption: '情况二：同样是 70% → 73%，但 B 多对 16 道、又多错 13 道。p = 0.71：<b>基本是抛硬币</b>，还说明两个版本的行为差异很大，需要看具体题。' },
        { t: [60, 0, 10, 30], p: 0.002, caption: '情况三：B 多对 10 道、一道没多错（60% → 70%）。p ≈ 0.002，这才算站得住。实务标准：分差超过噪声、在配对分析中成立、<b>能复现</b>，每个配置跑 3–5 个种子；同时验证多个假设，还要收紧阈值。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="sg-main"></div><div class="sg-st stat-row"></div>';
      const ci = (p, n) => { const h2 = 1.96 * Math.sqrt(p * (1 - p) / n); return [p - h2, p + h2]; };
      return {
        render(s) {
          const box = stage.querySelector('.sg-main');
          if (s.n) {
            delete box.dataset.mode;
            const A = ci(0.7, s.n), B = ci(0.73, s.n);
            const sc = v => (v - 0.5) / 0.4; // 50%..90% 映射到条形宽度
            bars(box, [
              { k: 'a', label: '旧模型', v: sc(0.7), cls: 'off', text: `70%${s.ci ? ` ±${((A[1] - 0.7) * 100).toFixed(1)}` : ''}`, ...(s.ci ? { lo: sc(A[0]), hi: sc(A[1]) } : {}) },
              { k: 'b', label: '新模型', v: sc(0.73), cls: 'on', text: `73%${s.ci ? ` ±${((B[1] - 0.73) * 100).toFixed(1)}` : ''}`, ...(s.ci ? { lo: sc(B[0]), hi: sc(B[1]) } : {}) },
            ]);
            stats(stage.querySelector('.sg-st'), [['题数 n', s.n], ['坐标轴', '<span style="font-size:14px">50% — 90%</span>']]);
            return;
          }
          const [both, aOnly, bOnly, none] = s.t;
          box.dataset.mode = 'table';
          box.innerHTML = `<div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1fr);gap:6px;max-width:440px;font-size:13px;text-align:center">
            <span></span><b>B 对</b><b>B 错</b>
            <b style="text-align:right">A 对</b><div class="node off">${both}</div><div class="node ${s.p != null ? 'bad' : 'on'}">${aOnly}</div>
            <b style="text-align:right">A 错</b><div class="node ${s.p != null ? 'ok' : 'on'}">${bOnly}</div><div class="node off">${none}</div></div>`;
          stats(stage.querySelector('.sg-st'), [['A / B 成功率', `${both + aOnly}% / ${both + bOnly}%`], ['不一致对', `${bOnly} : ${aOnly}`], ['McNemar p', s.p == null ? '—' : s.p, s.p == null ? '' : s.p < 0.05 ? 'ok' : 'warn']]);
        },
      };
    },
  });

  // ───────────────────────── 7.3 Harness 迭代 ─────────────────────────
  const HROWS = [
    ['H1', '加导航提示', '25%→25%', '0.47×', '没提高，沿用原提示', 'bad'],
    ['H5', 'accessibility feed → UIAutomator', '25%→100%', '2.498×', '有效但太费 token', 'warn'],
    ['H5C', '精简 UIAutomator 元素树', '100%→100%', '0.506×', '进入完整复测', 'ok'],
  ];
  define('harness-iteration', {
    title: '从 Benchmark 报告到改进：每轮只改一个变量',
    ms: 3800,
    scenarios: [
      { id: 'loop', label: 'Wi-Fi 子集三轮', steps: [
        { rows: 0, check: true, caption: '原则：看到分数下降，<b>先检查评测系统，再动 Agent</b>。资源不足被杀进程、验证器 bug、用例和生产脱节，在数字上都和模型退化一模一样，只有回看轨迹才能区分。' },
        { rows: 0, cluster: true, caption: 'AndroidWorld 116 项任务各跑一次，总成功率约 88%。但四项 <code>SystemWifiTurn*</code> 里挂了三项，轨迹里反复来回导航、确认不了最终状态。<b>先找失败集中在哪</b>。' },
        { rows: 1, caption: 'H1 先试最便宜的：假设 Agent 只是“不知道路”，补上导航提示。成功率不变。<b>提示写得再详细，也补不回 Agent 根本没看到的信息</b>。' },
        { rows: 2, caption: 'H5 检查 Agent 到底看见了什么：把 API 35 上不兼容的 accessibility feed 换成 UIAutomator 元素树。25% → 100%，但 token 涨到 2.5 倍。' },
        { rows: 3, caption: 'H5C 不加新信息，只删掉不可见、无文字、不能操作的容器节点：成功率保持，token 减半。同一个模型，只改 Harness 怎样表示界面，先后解决了“能不能做成”和“做成是否划算”。' },
        { rows: 3, next: true, caption: '但每组只有 4 项任务，<b>不能把子集上的 4/4 写成系统 100%</b>。下一步：116 项 × 5 个种子完整复测，成功率不降、token ≤ 75%、延迟 ≤ 1.5 倍，才能谈部署。一轮证据只支持与它规模相称的下一步。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="hi-top"></div><div class="hi-rows"></div><div class="hi-next"></div>';
      return {
        render(s) {
          stage.querySelector('.hi-top').innerHTML = s.check ? `<div class="legend enter" style="margin:0 0 6px">${pill('acc', '① 评测环境资源够吗')}${pill('acc', '② 验证器有 bug 吗')}${pill('acc', '③ 用例像生产吗')}<span>→ 再动 Agent</span></div>`
            : s.cluster ? `<div class="legend enter" style="margin:0 0 6px">${pill('', '总体 ≈ 88%')}${['On', 'Off', 'On', 'Off'].map((x, i) => pill(i === 1 ? 'ok' : 'bad', `SystemWifiTurn${x} ${i === 1 ? '✓' : '✗'}`)).join('')}</div>` : '';
          syncList(stage.querySelector('.hi-rows'), HROWS.slice(0, s.rows), r => r[0], () => h('div', { class: 'panel enter', style: { margin: '4px 0', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', fontSize: '13px' } }), (el, r) => {
            el.innerHTML = `<b style="flex:0 0 40px">${r[0]}</b><span style="flex:1 1 160px;min-width:0">${r[1]}</span>${pill(r[5], '成功率 ' + r[2])}${pill(r[0] === 'H5' ? 'warn' : '', 'token ' + r[3])}<span class="muted" style="font-size:12px">${r[4]}</span>`;
          });
          stage.querySelector('.hi-next').innerHTML = s.next ? `<div class="stat-row enter"><div class="stat"><div class="k">完整复测</div><div class="v">116 × 5</div></div><div class="stat"><div class="k">token 上限</div><div class="v">≤ 75%</div></div><div class="stat"><div class="k">延迟上限</div><div class="v">≤ 1.5×</div></div></div>` : '';
        },
      };
    },
  });

  // ───────────────────────── 7.3 AB 测试 ─────────────────────────
  define('ab-test', {
    title: 'AB 测试：区分机制、目标和护栏',
    ms: 3600,
    scenarios: [
      { id: 'plan', label: '缩短计划文件', steps: [
        { show: ['mech'], caption: '要验证的改动：让 Coding Agent 写更短的计划文件。实验组的计划长度降了 40%。这是<b>机制指标</b>：你直接改变的东西（以下数字均为示意）。' },
        { show: ['mech', 'goal'], goal: [0.01, -0.004, 0.024], caption: '真正的<b>目标指标</b>是会话级成本。计划短了，可能因为不够详细，带来更多“编辑—检查—编辑”循环。成本下降 1%，但区间跨过 0。' },
        { show: ['mech', 'goal', 'guard'], goal: [0.01, -0.004, 0.024], guard: [0.001, 0.2], caption: '<b>护栏指标</b>是不能变差的底线：拒绝率、用户满意度、错误率。这次都没越线。' },
        { show: ['mech', 'goal', 'guard'], goal: [0.01, -0.004, 0.024], guard: [0.001, 0.2], decide: 'inconclusive', caption: '<code>ab_decide</code>：护栏没越线，但目标区间跨 0，结论是 inconclusive：继续收集数据。<b>机制指标再漂亮也不是上线理由</b>，所以它根本不进决策函数。' },
      ] },
      { id: 'guard', label: '护栏越线', steps: [
        { show: ['mech', 'goal', 'guard'], goal: [0.05, 0.03, 0.07], guard: [0.004, 0.1], caption: '另一组更激进的变体：成本降 5%，区间整体大于 0，看起来可以上线。' },
        { show: ['mech', 'goal', 'guard'], goal: [0.05, 0.03, 0.07], guard: [0.004, 0.1], decide: 'stop:拒绝率', caption: '但拒绝率涨了 0.4 个点，超过允许的 0.2：<b>stop</b>。护栏越线，目标再好也要停。再配上多臂设计（控制组 + 三个渐进变体），就能看出剂量—效应关系，找到最优点。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="ab-m"></div><div class="ab-d"></div>';
      return {
        render(s) {
          const rows = [];
          if (s.show.includes('mech')) rows.push(`<div class="panel enter" style="margin:4px 0"><h4>机制指标 · 计划长度</h4>${pill('acc', '−40%')} <span class="muted" style="font-size:12px">你直接改变的东西</span></div>`);
          if (s.show.includes('goal')) {
            const [d, lo, hi] = s.goal;
            rows.push(`<div class="panel enter" style="margin:4px 0"><h4>目标指标 · 会话成本下降（B − A）</h4>${pill(lo > 0 ? 'ok' : 'warn', `${(d * 100).toFixed(0)}%，95% 区间 ${(lo * 100).toFixed(1)}% 到 ${(hi * 100).toFixed(1)}%`)}</div>`);
          }
          if (s.show.includes('guard')) {
            const [rej, sat] = s.guard;
            rows.push(`<div class="panel enter" style="margin:4px 0"><h4>护栏指标（越大越差）</h4>${pill(rej > 0.002 ? 'bad' : 'ok', `拒绝率 +${(rej * 100).toFixed(1)} 点 / 上限 0.2`)} ${pill(sat > 0.5 ? 'bad' : 'ok', `不满意率 +${sat.toFixed(1)} 点 / 上限 0.5`)}</div>`);
          }
          stage.querySelector('.ab-m').innerHTML = rows.join('');
          stage.querySelector('.ab-d').innerHTML = s.decide ? `<div class="stat-row enter"><div class="stat"><div class="k">ab_decide(…)</div><div class="v" style="color:${s.decide.startsWith('stop') ? FG.bad : FG.warn}">${s.decide}</div></div></div>` : '';
        },
      };
    },
  });
})();
