/* 模块 6 的动画：三种事件策略、打断占位符、原生异步、语音三范式、延迟瀑布、快慢思考、视觉定位、观察接口、机器人闭环 */
(function () {
  const { define, h, syncList, esc } = window.Anim;

  function renderMessages(box, msgs) {
    syncList(box, msgs, m => m.k, () => h('div', { class: 'msg' }), (el, m) => {
      el.className = `msg ${m.role}${m.cls ? ' ' + m.cls : ''}`;
      el.innerHTML = `<span class="role">${esc(m.label || m.role)}</span>${m.html}`;
    });
  }
  const pill = (cls, t) => `<span class="pill ${cls}">${t}</span>`;
  const nodeRow = (box, nodes, state) => syncList(box, nodes, n => n.id, () => h('div', { class: 'node', style: { flex: '1 1 80px', fontSize: '13px', padding: '6px 8px' } }), (el, n) => {
    el.className = `node ${state[n.id] || ''}`;
    el.innerHTML = n.name;
  });
  const SEG_BG = { on: 'var(--accent-soft)', ok: 'var(--ok-soft)', bad: 'var(--bad-soft)', warn: 'var(--warn-soft)', off: 'var(--surface-2)' };
  const SEG_FG = { on: 'var(--accent)', ok: 'var(--ok)', bad: 'var(--bad)', warn: 'var(--warn)', off: 'var(--muted)' };
  // 甘特图：rows=[{id,label}]，segs=[{k,row,from,to,label,cls}]，axis=[起点,终点]
  function gantt(box, axis, rows, segs, ticks) {
    const span = axis[1] - axis[0];
    const pct = v => ((v - axis[0]) / span) * 100;
    if (box.dataset.rows !== rows.map(r => r.id).join()) {
      box.dataset.rows = rows.map(r => r.id).join();
      box.innerHTML = rows.map(r => `<div style="display:flex;align-items:center;gap:6px;margin:4px 0"><div style="flex:0 0 64px;font-size:12px;color:var(--muted);text-align:right">${r.label}</div><div class="g-track" data-row="${r.id}" style="position:relative;flex:1;height:26px;background:var(--surface-2);border-radius:6px;min-width:0"></div></div>`).join('')
        + '<div style="display:flex;gap:6px"><div style="flex:0 0 64px"></div><div class="g-ticks" style="position:relative;flex:1;height:16px;font-size:10.5px;color:var(--muted)"></div></div>';
    }
    rows.forEach(r => {
      const track = box.querySelector(`.g-track[data-row="${r.id}"]`);
      syncList(track, segs.filter(s => s.row === r.id), s => s.k, () => h('div', { style: { position: 'absolute', top: '3px', bottom: '3px', borderRadius: '4px', fontSize: '11px', lineHeight: '20px', padding: '0 4px', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis', transition: 'all .4s ease', boxSizing: 'border-box' } }), (el, s) => {
        el.style.left = pct(s.from) + '%';
        el.style.width = Math.max(pct(s.to) - pct(s.from), 1.2) + '%';
        el.style.background = SEG_BG[s.cls || 'on'];
        el.style.color = SEG_FG[s.cls || 'on'];
        el.style.border = `1px solid ${SEG_FG[s.cls || 'on']}`;
        el.title = s.label.replace(/<[^>]+>/g, '');
        el.innerHTML = s.label;
      });
    });
    box.querySelector('.g-ticks').innerHTML = (ticks || []).map(t => `<span style="position:absolute;left:${pct(t.v)}%;transform:translateX(-50%);white-space:nowrap">${t.l}</span>`).join('');
  }

  // ───────────────────────── 6.1 三种事件处理策略 ─────────────────────────
  const STRATS = [
    { id: 'cancel', name: '取消式<div class="muted" style="font-size:11px">提前制造安全点</div>' },
    { id: 'queue', name: '队列式<div class="muted" style="font-size:11px">等下一个安全点</div>' },
    { id: 'parallel', name: '并行式<div class="muted" style="font-size:11px">另起一个循环</div>' },
  ];
  define('event-strategies', {
    title: '三种事件处理策略：打断、排队、并行',
    ms: 3400,
    scenarios: [
      { id: 'queue', label: '队列式', steps: [
        { m: ['q1', 'q2'], lane: { tool: ['write_report 运行中…', 'on'] }, caption: '用户让 Agent 写季度报告，<code>write_report</code> 要跑一阵子。此刻是两个安全点之间：模型在等工具返回。' },
        { m: ['q1', 'q2'], ev: 'User：附件也带上', st: 'queue', held: 1, lane: { tool: ['write_report 运行中…', 'on'] }, caption: '用户补充了一句。这是常规输入（<code>user.input</code>）：<b>不打断</b>，放进队列。' },
        { m: ['q1', 'q2'], ev: 'User：抄送李四', st: 'queue', held: 2, lane: { tool: ['write_report 运行中…', 'on'] }, caption: '又来一句，同样排队。注意模型一次都还没被调用。' },
        { m: ['q1', 'q2', 'q3', 'q4'], held: 0, lane: { tool: ['已返回', 'ok'] }, caption: '工具返回 = 自然的安全点（规则 5）。先追加配对的工具结果，再把排队的事件<b>一次性</b>追加，每条带上“未处理事件 i/n”标记，末尾一句汇总。' },
        { m: ['q1', 'q2', 'q3', 'q4', 'q5'], lane: { tool: ['已返回', 'ok'] }, caption: '只多了一次模型调用就处理完两条补充。标记是为了对抗<b>注意力分散</b>：批量事件里，模型容易只回应最后一条（练习 6.1b）。' },
      ] },
      { id: 'cancel', label: '取消式', steps: [
        { m: ['c1', 'c2'], lane: { tool: ['search_contacts 运行中…', 'on'] }, caption: '原书的例子：Agent 在帮用户写邮件，正在搜索联系人。' },
        { m: ['c1', 'c2'], ev: 'User：等一下，先帮我查一下明天的天气', urgent: true, st: 'cancel', lane: { tool: ['search_contacts 运行中…', 'on'] }, caption: '用户打断，改变了优先级。紧急事件走取消式：<b>不等工具返回</b>，现在就制造一个安全点。' },
        { m: ['c1', 'c2', 'c3', 'c4'], lane: { tool: ['转入后台继续跑', 'warn'] }, caption: '没跑完的工具<b>不丢掉</b>，转入后台；轨迹里先放一条明确的占位符，让 assistant 的工具调用仍然有配对结果（规则 3），再追加用户的话。' },
        { m: ['c1', 'c2', 'c3', 'c4', 'c5'], lane: { tool: ['转入后台继续跑', 'warn'] }, caption: '模型先回答天气。它知道联系人搜索还没结果，所以不编邮箱地址。' },
        { m: ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'], ev: 'tool.result（任务 c1）', st: 'queue', lane: { tool: ['真实结果到达', 'ok'] }, caption: '后台的真实结果到了。它作为<b>带来源和任务 ID 的新事件</b>进入轨迹（规则 2），工具结果一律走队列。' },
        { m: ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7'], lane: { tool: ['真实结果到达', 'ok'] }, caption: 'Agent 把结果归到正确的任务，接着把邮件写完。用户点“停止”是另一种取消：工具会被真的取消，见下一个动画。' },
      ] },
      { id: 'parallel', label: '并行式', steps: [
        { m: ['p1', 'p2'], lane: { tool: ['analyze_logs 运行中…', 'on'] }, caption: 'Agent 在分析大量日志，这一步要很久。' },
        { m: ['p1', 'p2'], ev: 'User：今天天气怎么样？', st: 'parallel', lane: { tool: ['analyze_logs 运行中…', 'on'], side: ['并行会话：系统提示 + 这一个问题', 'on'] }, caption: '与主任务无关、要快、成本低。取消式会打断重要的主任务，队列式又让用户干等：<b>另起一个推理会话</b>。' },
        { m: ['p1', 'p2'], out: '今天多云，18℃。', lane: { tool: ['analyze_logs 运行中…', 'on'], side: ['已回答', 'ok'] }, caption: '并行会话直接把答案发给用户。主任务没有被打断，主轨迹也没被碰过。' },
        { m: ['p1', 'p2', 'p3', 'p4'], lane: { tool: ['已返回', 'ok'], side: ['已回答', 'ok'] }, caption: '到下一个安全点，这段问答作为一条<b>明确标注“并行会话”</b>的记录并入主轨迹，模型之后才不会困惑“用户什么时候问过天气”。' },
        { m: ['p1', 'p2', 'p3', 'p4', 'p5'], lane: { tool: ['已返回', 'ok'], side: ['已回答', 'ok'] }, caption: '硬编码规则有局限：“马上停下”要取消，“今天天气怎么样”要并行，“报告用中文发我”要排队。原书建议用<b>轻量级分类 LLM 当路由器</b>（<code>llm_router</code>），输出不合法时退回规则。' },
      ] },
    ],
    mount(stage) {
      const M = {
        q1: { k: 'q1', role: 'user', html: '写一份季度报告发给张三。' },
        q2: { k: 'q2', role: 'assistant', html: '→ <code>write_report(quarter="Q3")</code>　<span class="pill">c1</span>' },
        q3: { k: 'q3', role: 'tool', html: '<span class="pill">c1</span>　报告已生成：Q3.pdf' },
        q4: { k: 'q4', role: 'user', label: 'user · 批量事件', html: '[未处理事件 1/2] User：附件也带上<br>[未处理事件 2/2] User：抄送李四<br><span class="sub">上面有 2 个未处理事件，包括 2 条用户消息。请确保回应涵盖所有信息。</span>' },
        q5: { k: 'q5', role: 'assistant', html: '报告已发给张三，附上了 Q3.pdf，并抄送李四。', cls: 'good' },
        c1: { k: 'c1', role: 'user', html: '给张三写封邮件，约周五开会。' },
        c2: { k: 'c2', role: 'assistant', html: '→ <code>search_contacts(name="张三")</code>　<span class="pill">c1</span>' },
        c3: { k: 'c3', role: 'tool', html: '<span class="pill">c1</span>　[任务 c1 仍在后台执行。请先处理新事件；真实结果会作为单独的事件到达，在那之前不要假设它的结果]', cls: 'dim' },
        c4: { k: 'c4', role: 'user', html: 'User：等一下，先帮我查一下明天的天气' },
        c5: { k: 'c5', role: 'assistant', html: '明天晴，最高 22℃。联系人还在查，查到后继续写邮件。' },
        c6: { k: 'c6', role: 'user', label: 'user · 事件', html: 'Tool result from search_contacts（任务 c1）：张三 &lt;zhang@example.com&gt;' },
        c7: { k: 'c7', role: 'assistant', html: '草稿：致 zhang@example.com，“周五下午三点方便开个会吗？……”', cls: 'good' },
        p1: { k: 'p1', role: 'user', html: '分析一下这 10 万行访问日志，找出异常流量。' },
        p2: { k: 'p2', role: 'assistant', html: '→ <code>analyze_logs(path="access.log")</code>　<span class="pill">c1</span>' },
        p3: { k: 'p3', role: 'tool', html: '<span class="pill">c1</span>　发现 3 段异常峰值……' },
        p4: { k: 'p4', role: 'user', label: 'user · 事件', html: 'parallel.note from parallel：用户问“今天天气怎么样？”，已在并行会话中回答：今天多云，18℃。' },
        p5: { k: 'p5', role: 'assistant', html: '日志分析完成：异常集中在凌晨 2 点到 3 点……', cls: 'good' },
      };
      stage.innerHTML = `<div style="display:flex;gap:8px;align-items:stretch;flex-wrap:wrap;margin-bottom:6px">
          <div class="es-ev" style="flex:1 1 200px;min-width:0"></div>
          <div class="es-st" style="flex:2 1 260px;display:flex;gap:6px"></div></div>
        <div class="es-lanes" style="font-size:12.5px;margin-bottom:6px"></div>
        <div class="m-msgs"></div><div class="es-out"></div>`;
      return {
        render(s) {
          stage.querySelector('.es-ev').innerHTML = s.ev
            ? `<div class="node ${s.urgent ? 'bad' : 'on'} enter" style="text-align:left;font-size:13px;height:100%;box-sizing:border-box"><span class="muted" style="font-size:11px">新事件${s.urgent ? ' · priority=urgent' : ''}</span><br>${esc(s.ev)}</div>`
            : `<div class="node off" style="font-size:13px;height:100%;box-sizing:border-box">没有新事件${s.held ? `<br>${pill('warn', `队列里 ${s.held} 条`)}` : ''}</div>`;
          nodeRow(stage.querySelector('.es-st'), STRATS, Object.fromEntries(STRATS.map(x => [x.id, s.st ? (x.id === s.st ? 'on' : 'off') : ''])));
          const lane = s.lane || {};
          stage.querySelector('.es-lanes').innerHTML = [['tool', '后台工具'], ['side', '并行会话']].filter(([id]) => lane[id]).map(([id, name]) =>
            `<div style="display:flex;gap:6px;align-items:center;margin:2px 0"><span class="muted" style="flex:0 0 64px;text-align:right">${name}</span>${pill(lane[id][1] === 'on' ? 'acc' : lane[id][1], lane[id][0])}${s.held && id === 'tool' ? ' ' + pill('warn', `排队 ${s.held}`) : ''}</div>`).join('');
          renderMessages(stage.querySelector('.m-msgs'), s.m.map(k => M[k]));
          stage.querySelector('.es-out').innerHTML = s.out ? `<div class="msg assistant good enter"><span class="role">并行会话 → 用户</span>${esc(s.out)}</div>` : '';
        },
      };
    },
  });

  // ───────────────────────── 6.1 打断时的占位符 ─────────────────────────
  define('interrupt-placeholder', {
    title: '打断时的占位符：让轨迹合法，又不让模型编造',
    ms: 3400,
    scenarios: [
      { id: 'raw', label: '直接追加', steps: [
        { m: ['u1', 'a1'], check: null, caption: '工具 c1 还在跑，用户打断。最直接的做法：把新消息追加到轨迹末尾，马上调用模型。' },
        { m: ['u1', 'a1', 'n1'], check: 'bad', verdict: '400：assistant 消息里的 tool_call c1 没有对应的 tool 结果', caption: '许多接口要求每个工具调用后面紧跟它的结果。<b>悬空的调用让请求直接被拒</b>。这个限制来自所选的协议与模型组合，并非所有模型都如此。' },
      ] },
      { id: 'fake', label: '伪造结果', steps: [
        { m: ['u1', 'a1', 'f1', 'n1'], check: 'warn', verdict: '格式合法，语义错误', caption: '为了凑配对，塞一条“看起来像成功”的结果进去。接口不报错了。' },
        { m: ['u1', 'a1', 'f1', 'n1', 'f2'], check: 'bad', verdict: '模型基于不存在的数据行动', caption: '模型当真了：用一个<b>根本没查到的邮箱</b>写完了邮件。原书原话：未完成的工具结果用显式占位符表示，<b>不能伪造成功</b>。' },
      ] },
      { id: 'ph', label: '占位符', steps: [
        { m: ['u1', 'a1', 'p1', 'n1'], check: 'ok', verdict: '配对完好；c1 明确标为“仍在后台执行”', caption: '兼容方案的规则 3：为没跑完的调用补一条<b>占位符</b>，内容说清“没完成、结果会另行送达、别假设它”，再追加新事件（练习 6.1c 的 <code>interrupt</code>）。' },
        { m: ['u1', 'a1', 'p1', 'n1', 'p2'], check: 'ok', verdict: '配对完好', caption: '模型先处理新问题，并且<b>没有假设</b>联系人的结果。' },
        { m: ['u1', 'a1', 'p1', 'n1', 'p2', 'p3', 'p4'], check: 'ok', verdict: '迟到的结果按任务 ID 归位', caption: '真实结果到达时，以带来源和任务 ID 的事件进入轨迹。风险仍在：模型可能把“已启动”误当“已完成”，所以评估要专门检查<b>是否编造了未到达的数据</b>。' },
      ] },
      { id: 'stop', label: '用户点停止', steps: [
        { m: ['u1', 'a1', 's1', 's2'], check: 'ok', verdict: '工具已取消（执行器收到 CancelledError）', caption: '<code>user.interrupt</code> 是更强的取消：工具被真的取消，占位符写“已被用户取消，没有结果”，之后<b>不会</b>有迟到的事件。' },
        { m: ['u1', 'a1', 's1', 's2', 's3'], check: 'ok', verdict: '工具已取消', caption: '但要记住：<b>接收一条“停止”消息本身不会撤销已经发生的动作</b>。取消要靠执行器响应取消信号（像 Go 里检查 <code>ctx.Done()</code>），已经发出的邮件收不回来。' },
      ] },
    ],
    mount(stage) {
      const M = {
        u1: { k: 'u1', role: 'user', html: '给张三写封邮件，约周五开会。' },
        a1: { k: 'a1', role: 'assistant', html: '→ <code>search_contacts(name="张三")</code>　<span class="pill">c1</span>　<span class="muted">（执行中…）</span>' },
        n1: { k: 'n1', role: 'user', html: '等一下，先帮我查一下明天的天气' },
        f1: { k: 'f1', role: 'tool', html: '<span class="pill">c1</span>　找到：张三 &lt;zhangsan@company.com&gt;', cls: 'bad' },
        f2: { k: 'f2', role: 'assistant', html: '明天晴。另外邮件已写好，发往 zhangsan@company.com。', cls: 'bad' },
        p1: { k: 'p1', role: 'tool', html: '<span class="pill">c1</span>　[任务 c1 仍在后台执行。请先处理新事件；真实结果会作为单独的事件到达，在那之前不要假设它的结果]' },
        p2: { k: 'p2', role: 'assistant', html: '明天晴，最高 22℃。张三的联系方式还在查。' },
        p3: { k: 'p3', role: 'user', label: 'user · 事件', html: 'Tool result from search_contacts（任务 c1）：张三 &lt;zhang@example.com&gt;' },
        p4: { k: 'p4', role: 'assistant', html: '草稿：致 zhang@example.com……', cls: 'good' },
        s1: { k: 's1', role: 'tool', html: '<span class="pill">c1</span>　[任务 c1 已被用户取消，没有结果]' },
        s2: { k: 's2', role: 'user', html: '停止' },
        s3: { k: 's3', role: 'assistant', html: '好的，已停止，没有发出任何邮件。', cls: 'good' },
      };
      stage.innerHTML = '<div class="ip-check" style="margin-bottom:6px"></div><div class="m-msgs"></div>';
      return {
        render(s) {
          const c = s.check;
          stage.querySelector('.ip-check').innerHTML = `<div class="legend" style="margin:0"><span class="muted" style="font-size:12px">发给模型之前的配对检查：</span>${c ? pill(c, (c === 'ok' ? '✓ ' : c === 'bad' ? '✗ ' : '! ') + s.verdict) : pill('', '尚未发送')}</div>`;
          renderMessages(stage.querySelector('.m-msgs'), s.m.map(k => M[k]));
        },
      };
    },
  });

  // ───────────────────────── 6.1 模型原生异步 ─────────────────────────
  const NA_ROWS = [{ id: 'user', label: '用户' }, { id: 'model', label: '模型' }, { id: 'tool', label: '查询场地' }];
  const NA_TICKS = [0, 2, 4, 6, 8, 10, 12].map(v => ({ v, l: v + 's' }));
  define('native-async', {
    title: '模型原生异步：等待不阻塞，中途可以改需求',
    ms: 3200,
    scenarios: [
      { id: 'sync', label: '同步工具', steps: [
        { segs: ['m0', 't1'], caption: '原书实验 6-3 的任务：为一次会议选场地。<code>lookup_venues</code> 要 8 秒。同步工具：调用发出后模型就在等。' },
        { segs: ['m0', 't1', 'mw'], caption: '8 秒里<b>没有任何输出</b>。不依赖查询结果的准备工作（议程、清单）也被一起卡住了。' },
        { segs: ['m0', 't1', 'mw', 'mA'], res: ['', '选 A'], caption: '结果到了才继续，选出场地 A。' },
      ] },
      { id: 'async', label: '异步工具', steps: [
        { segs: ['m0', 't1'], caption: '同一个模型、同一个任务，只把工具定义改成 <code>async: true</code>。' },
        { segs: ['m0', 't1', 'mp'], caption: '<b>发起行动和获得结果分开</b>：查询在跑，模型先写不依赖结果的准备清单。' },
        { segs: ['m0', 't1', 'mp', 'mA'], res: ['', '选 A'], caption: '必须依据结果的决策，留到结果到达之后。关键是分清工作的依赖关系。' },
      ] },
      { id: 'steer', label: '异步 + 中途引导', steps: [
        { segs: ['m0', 't1', 'mp'], caption: '工具已经在跑，模型在写准备清单。' },
        { segs: ['m0', 't1', 'mp', 'u1', 'u2'], caption: '用户中途补充两条：预算改为 1000，人数改为 10。<b>回合中途引导</b>（mid-turn steering）让它们不必等这一轮结束。' },
        { segs: ['m0', 't1', 'mp2', 'u1', 'u2'], caption: '更新被接受，并带入后续计划。注意：改计划<b>不等于</b>停止正在运行的工具，查询仍然只执行一次。' },
        { segs: ['m0', 't1', 'mp2', 'u1', 'u2', 'mB'], res: ['ok', '选 B'], caption: '真实结果仍用原始的 call_id 归还；两条约束同时生效，选出 B。执行、取消和状态管理仍由运行时负责。' },
      ] },
      { id: 'none', label: '不支持的模型', steps: [
        { segs: ['m0', 't1', 'mw', 'u1'], caption: '换一个不支持原生能力的模型，发出同样的中途更新。' },
        { segs: ['m0', 't1', 'mw', 'u1x'], res: ['bad', 'steering_not_supported'], caption: '接口明确拒绝。这时就回到兼容方案：事件队列、占位符、任务句柄。<b>代码里用了 asyncio，不等于模型具备原生异步能力</b>。' },
      ] },
    ],
    mount(stage) {
      const S = {
        m0: { k: 'm0', row: 'model', from: 0, to: 0.8, label: '发起', cls: 'on' },
        t1: { k: 't1', row: 'tool', from: 0.8, to: 8.8, label: 'lookup_venues · 8s', cls: 'warn' },
        mw: { k: 'mw', row: 'model', from: 0.8, to: 8.8, label: '等待（无输出）', cls: 'off' },
        mp: { k: 'mp', row: 'model', from: 0.8, to: 5, label: '写准备清单', cls: 'ok' },
        mp2: { k: 'mp', row: 'model', from: 0.8, to: 6.2, label: '清单 + 按新约束调整', cls: 'ok' },
        u1: { k: 'u1', row: 'user', from: 2.2, to: 3.8, label: '预算 1000', cls: 'on' },
        u1x: { k: 'u1', row: 'user', from: 2.2, to: 3.8, label: '预算 1000', cls: 'bad' },
        u2: { k: 'u2', row: 'user', from: 4, to: 5, label: '10 人', cls: 'on' },
        mA: { k: 'mR', row: 'model', from: 8.8, to: 11, label: '比较 → A', cls: 'on' },
        mB: { k: 'mR', row: 'model', from: 8.8, to: 11, label: '比较 → B', cls: 'ok' },
      };
      stage.innerHTML = '<div class="na-g"></div><div class="na-res" style="margin-top:6px;min-height:22px"></div>';
      return {
        render(s) {
          gantt(stage.querySelector('.na-g'), [0, 12], NA_ROWS, s.segs.map(k => S[k]), NA_TICKS);
          stage.querySelector('.na-res').innerHTML = s.res ? `<span class="muted" style="font-size:12.5px">结果：</span>${pill(s.res[0], s.res[1])}` : '';
        },
      };
    },
  });

  // ───────────────────────── 6.2 语音交互的三种范式 ─────────────────────────
  define('voice-paradigms', {
    title: '语音三范式：级联、端到端 Omni、全双工',
    ms: 3600,
    scenarios: [
      { id: 'cascade', label: '级联', steps: [
        { nodes: ['VAD', 'ASR', 'LLM', 'TTS'], on: 0, m: ['v1'], caption: '用户报卡号，说到一半停下来想了想。级联流水线的第一关是 <b>VAD</b>：靠一段静音判断“说完了”。' },
        { nodes: ['VAD', 'ASR', 'LLM', 'TTS'], on: 1, m: ['v1', 'v2'], caption: '静音超过阈值，VAD 判定说完，<b>把一个数字切成了两半</b>。ASR 只拿到前半段文字。' },
        { nodes: ['VAD', 'ASR', 'LLM', 'TTS'], on: 2, m: ['v1', 'v2', 'v3'], caption: '转成纯文本时，“嗯……”里的犹豫、语气和背景声都丢了。LLM 只看到一串不完整的数字。' },
        { nodes: ['VAD', 'ASR', 'LLM', 'TTS'], on: 3, m: ['v1', 'v2', 'v3', 'v4'], caption: '模块清晰、易替换、易调试，代价是<b>延迟累积</b>和<b>副语言信息在接口处丢失</b>。' },
      ] },
      { id: 'omni', label: '端到端 Omni', steps: [
        { nodes: ['VAD', 'Omni 模型（音频进，音频出）'], on: 1, m: ['v1', 'o1'], caption: '同一个模型直接听音频、直接说。它听得出“嗯……”是在想，而不是说完了。' },
        { nodes: ['VAD', 'Omni 模型（音频进，音频出）'], on: 0, m: ['v1', 'o1', 'o2'], caption: '可是发言权仍由 VAD 划分：Omni 仍然<b>假设轮流说话</b>，报数字时的停顿照样可能被误判为说完。' },
        { nodes: ['VAD', 'Omni 模型（音频进，音频出）'], on: 1, m: ['v1', 'o1', 'o2', 'o3'], caption: '优势在延迟和非文字信息（语气、情绪、唱歌），代价是训练和调试成本更高。' },
      ] },
      { id: 'duplex', label: '全双工', steps: [
        { nodes: ['持续听', '持续说', '持续决策'], on: 0, m: ['v1', 'd1'], caption: '全双工不再预设轮次：模型一直在听、一直可以说，并不断决定继续、停顿、打断还是调用工具。' },
        { nodes: ['持续听', '持续说', '持续决策'], on: 2, m: ['v1', 'd1', 'd2'], caption: '用户停顿时，它可以只说一声“嗯”表示在听，<b>等用户说完</b>。“该谁说话”成了模型自己的决策，而不是 VAD 的猜测。' },
        { nodes: ['持续听', '持续说', '持续决策'], on: 1, m: ['v1', 'd1', 'd2', 'd3', 'd4'], caption: '用户可以随时打断，它会停下来。复杂问题还可以委派给后台推理模型，前台继续维持话头（快慢分离，见后面的动画）。' },
      ] },
    ],
    mount(stage) {
      const M = {
        v1: { k: 'v1', role: 'user', label: '用户（语音）', html: '我的卡号是 6222 0215……<span class="muted">（嗯……停顿 0.8 秒）</span>……4409 0158' },
        v2: { k: 'v2', role: 'status', label: 'VAD + ASR', html: '静音 0.6s → 判定说完 → “我的卡号是 6222 0215”', cls: 'bad' },
        v3: { k: 'v3', role: 'status', label: 'LLM', html: '输入：纯文本“我的卡号是 6222 0215”（没有“嗯……”）' },
        v4: { k: 'v4', role: 'assistant', label: 'Agent（语音）', html: '您的卡号位数不对，请重新提供。', cls: 'bad' },
        o1: { k: 'o1', role: 'status', label: 'Omni', html: '听到：语气迟疑、未说完' },
        o2: { k: 'o2', role: 'status', label: 'VAD', html: '静音 0.6s → 仍然切断这一轮', cls: 'bad' },
        o3: { k: 'o3', role: 'assistant', label: 'Agent（语音）', html: '（语气更自然，但仍可能在用户想数字时插话）' },
        d1: { k: 'd1', role: 'status', label: '模型', html: '在听：数字还没报完，判断为思考停顿' },
        d2: { k: 'd2', role: 'assistant', label: 'Agent（语音）', html: '嗯。<span class="muted">（附和，不抢话）</span>', cls: 'good' },
        d3: { k: 'd3', role: 'user', label: '用户（语音）', html: '……4409 0158。哦不对，等一下——' },
        d4: { k: 'd4', role: 'assistant', label: 'Agent（语音）', html: '好的，您慢慢说。<span class="muted">（被打断，立刻停下）</span>', cls: 'good' },
      };
      stage.innerHTML = '<div class="vp-nodes" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px"></div><div class="m-msgs"></div>';
      return {
        render(s) {
          const nodes = s.nodes.map((n, i) => ({ id: 'n' + i + n, name: n }));
          nodeRow(stage.querySelector('.vp-nodes'), nodes, Object.fromEntries(nodes.map((n, i) => [n.id, i === s.on ? 'on' : ''])));
          renderMessages(stage.querySelector('.m-msgs'), s.m.map(k => M[k]));
        },
      };
    },
  });

  // ───────────────────────── 6.2 延迟瀑布 ─────────────────────────
  const LW_ROWS = [{ id: 'user', label: '用户说话' }, { id: 'asr', label: 'VAD / ASR' }, { id: 'llm', label: 'LLM' }, { id: 'tts', label: 'TTS' }];
  const LW_TICKS = [-600, -300, 0, 300, 600, 900].map(v => ({ v, l: (v > 0 ? '+' : '') + v }));
  define('latency-waterfall', {
    title: '首音延迟：串行累积、流式感知、推测执行',
    ms: 3200,
    scenarios: [
      { id: 'serial', label: '串行', steps: [
        { segs: ['sp', 'vad'], caption: '0 是用户停止说话的时刻。串行流水线先要<b>等一段静音</b>才敢确认说完（原书图 6-7：500–800ms）。' },
        { segs: ['sp', 'vad', 'asrF'], caption: '然后整段音频交给 ASR（50–200ms）。' },
        { segs: ['sp', 'vad', 'asrF', 'ttft', 'gen'], caption: 'LLM 首 token（100–500ms），再等它<b>生成完整回复</b>（100–300ms）。' },
        { segs: ['sp', 'vad', 'asrF', 'ttft', 'gen', 'tts1'], total: [950, 1], caption: 'TTS 首包（200–500ms）。全取下限是 <b>950ms</b>，全取上限 2.3 秒。这还是空载理想情况，生产环境的排队会进一步放大。' },
      ] },
      { id: 'stream', label: '流式感知', steps: [
        { segs: ['sp', 'asrS'], caption: '流式感知：VAD 检测到开始说话就<b>边听边转</b>，按间隔调用 ASR 生成临时转录。' },
        { segs: ['sp', 'asrS', 'vad', 'fin'], caption: '说完后只需确认最终文本（这里取 20ms），不必再整段识别。' },
        { segs: ['sp', 'asrS', 'vad', 'fin', 'llmS'], caption: 'LLM <b>分段输出</b>：第一段能念的文字一出来就交给 TTS（练习 6.2a 的 <code>split_for_tts</code>），不等完整回复。' },
        { segs: ['sp', 'asrS', 'vad', 'fin', 'llmS', 'tts2'], total: [850, 1], caption: '首音 850ms。省下的是整段 ASR 和“生成完整回复”。静音那 500ms 还在。' },
      ] },
      { id: 'spec', label: '推测执行 · 猜对', steps: [
        { segs: ['sp', 'asrS', 'p1', 'p2'], caption: '<b>推测执行</b>：每出一个新的临时转录，就取消上一次推测，用新文本调用 LLM。' },
        { segs: ['sp', 'asrS', 'p1', 'p2', 'p3', 'vad', 'fin'], caption: '最后一个临时转录“明天天气怎么样”在 0ms 发出，LLM 在<b>静音期间</b>就已经开工。' },
        { segs: ['sp', 'asrS', 'p1', 'p2', 'p3', 'vad', 'fin', 'tts3'], total: [720, 3], caption: '最终文本和最后一个临时转录一致，不用再调 LLM：首音 720ms。代价是 LLM 调了 3 次，<b>用算力换延迟</b>（练习 6.2b）。' },
      ] },
      { id: 'miss', label: '推测执行 · 猜错', steps: [
        { segs: ['sp', 'asrS', 'q1', 'q2', 'vad', 'fin'], caption: '另一句话：最后一个临时转录是“帮我订明天”，最终文本却是“帮我订明天的票”。' },
        { segs: ['sp', 'asrS', 'q1', 'q2x', 'vad', 'fin', 'llmS', 'tts2'], total: [850, 3], caption: '推测作废，重新调用。延迟退回流式感知的 850ms，还多花了两次调用。推测执行的收益取决于临时转录<b>有多常和最终结果一致</b>。' },
      ] },
    ],
    mount(stage) {
      const S = {
        sp: { k: 'sp', row: 'user', from: -600, to: 0, label: '说话中', cls: 'off' },
        vad: { k: 'vad', row: 'asr', from: 0, to: 500, label: '等静音 500', cls: 'warn' },
        asrF: { k: 'asrF', row: 'asr', from: 500, to: 550, label: 'ASR', cls: 'on' },
        asrS: { k: 'asrS', row: 'asr', from: -600, to: -10, label: '边听边转', cls: 'ok' },
        fin: { k: 'fin', row: 'asr', from: 500, to: 520, label: '确认', cls: 'on' },
        ttft: { k: 'ttft', row: 'llm', from: 550, to: 650, label: '首 token', cls: 'on' },
        gen: { k: 'gen', row: 'llm', from: 650, to: 750, label: '完整回复', cls: 'on' },
        llmS: { k: 'llmS', row: 'llm', from: 520, to: 650, label: '首段', cls: 'ok' },
        p1: { k: 'p1', row: 'llm', from: -400, to: -270, label: '明天', cls: 'off' },
        p2: { k: 'p2', row: 'llm', from: -200, to: -70, label: '明天天气', cls: 'off' },
        p3: { k: 'p3', row: 'llm', from: 0, to: 130, label: '…怎么样', cls: 'ok' },
        q1: { k: 'q1', row: 'llm', from: -300, to: -170, label: '帮我订', cls: 'off' },
        q2: { k: 'q2', row: 'llm', from: 0, to: 130, label: '帮我订明天', cls: 'on' },
        q2x: { k: 'q2', row: 'llm', from: 0, to: 130, label: '帮我订明天 ✗', cls: 'bad' },
        tts1: { k: 'tts', row: 'tts', from: 750, to: 950, label: '首包', cls: 'on' },
        tts2: { k: 'tts', row: 'tts', from: 650, to: 850, label: '首包', cls: 'ok' },
        tts3: { k: 'tts', row: 'tts', from: 520, to: 720, label: '首包', cls: 'ok' },
      };
      stage.innerHTML = '<div class="lw-g"></div><div class="lw-total stat-row" style="margin-top:6px"></div>';
      return {
        render(s) {
          gantt(stage.querySelector('.lw-g'), [-600, 1000], LW_ROWS, s.segs.map(k => S[k]), LW_TICKS);
          stage.querySelector('.lw-total').innerHTML = s.total
            ? `<div class="stat"><div class="k">首音（停止说话后）</div><div class="v">${s.total[0]} ms</div></div><div class="stat"><div class="k">LLM 调用</div><div class="v">${s.total[1]} 次</div></div>`
            : '<div class="stat"><div class="k">时间轴单位</div><div class="v" style="font-size:15px">毫秒</div></div>';
        },
      };
    },
  });

  // ───────────────────────── 6.2 快慢思考 ─────────────────────────
  define('fast-slow', {
    title: '快思考与慢思考：谁对用户说话',
    ms: 3400,
    scenarios: [
      { id: 'respond', label: '方案一：各自回答', steps: [
        { st: { fast: 'on', slow: 'on' }, m: ['u'], caption: '用户问：“这个套餐值得买吗？我经常出国。”方案一：快模型先回应，慢模型在后台独立推导，<b>两段话都念给用户</b>。' },
        { st: { fast: 'ok', slow: 'on' }, m: ['u', 'f1'], caption: '快模型几百毫秒内就开口了。' },
        { st: { fast: 'ok', slow: 'ok' }, m: ['u', 'f1', 's1'], caption: '几秒后慢模型发现套餐缺少国际漫游。用户在几秒内听到<b>相互冲突的答案</b>。根本原因：两个实例各自完成了一次独立思考。' },
      ] },
      { id: 'advise', label: '方案二：慢模型提醒', steps: [
        { st: { fast: 'on', slow: 'off' }, m: ['u'], caption: '方案二：只有快模型对用户说话。它带着一个 <code>think_deeply</code> 工具。' },
        { st: { fast: 'ok', slow: 'on' }, m: ['u', 'a1'], caption: '快模型判断这题需要深想：先说一句自然的过渡语，同时把问题交给后台。' },
        { st: { fast: 'ok', slow: 'ok' }, m: ['u', 'a1', 'a2'], caption: '慢模型的结论以 <code>[后台建议]</code> 的工具结果送回，<b>由快模型决定怎么说</b>（练习 6.2c）。' },
        { st: { fast: 'ok', slow: 'ok' }, m: ['u', 'a1', 'a2', 'a3'], caption: '用户只听到一个声音，前后一致。局限：通信间接，前台可能误解建议；后台完成前用户追问，前台只能靠自己。' },
      ] },
      { id: 'simple', label: '方案二：简单问题', steps: [
        { st: { fast: 'ok', slow: 'off' }, m: ['h', 'h1'], caption: '“你好”这种问题快模型直接回答，<b>慢模型完全不参与</b>。方案一里它会被重复处理一遍。' },
        { st: { fast: 'ok', slow: 'off' }, m: ['h', 'h1'], swap: true, caption: '快慢分离的工程优势：更强的思考模型发布后，<b>只换后台</b>，不必重训整套实时语音系统。方案三（Step-Audio R1 这类端到端思考）把两者统一在一个模型里，“边想边说”最紧密，代价是要一起重新训练。' },
      ] },
    ],
    mount(stage) {
      const M = {
        u: { k: 'u', role: 'user', label: '用户（语音）', html: '这个套餐值得买吗？我经常出国。' },
        f1: { k: 'f1', role: 'assistant', label: '快模型 → 用户', html: '这个套餐挺划算的，建议买。' },
        s1: { k: 's1', role: 'assistant', label: '慢模型 → 用户', html: '不建议：它不支持国际漫游。', cls: 'bad' },
        a1: { k: 'a1', role: 'assistant', label: '快模型 → 用户', html: '我帮你对比一下，稍等。<span class="muted">　→ think_deeply("套餐是否适合经常出国的人")</span>' },
        a2: { k: 'a2', role: 'tool', label: '慢模型 → 快模型', html: '[后台建议] 不适合：缺少国际漫游。' },
        a3: { k: 'a3', role: 'assistant', label: '快模型 → 用户', html: '仔细看了下，这个套餐不支持国际漫游，你经常出国的话不太合适。', cls: 'good' },
        h: { k: 'h', role: 'user', label: '用户（语音）', html: '你好' },
        h1: { k: 'h1', role: 'assistant', label: '快模型 → 用户', html: '你好！有什么可以帮你？', cls: 'good' },
      };
      stage.innerHTML = '<div class="fs-nodes" style="display:flex;gap:6px;margin-bottom:8px"></div><div class="m-msgs"></div><div class="fs-swap"></div>';
      return {
        render(s) {
          nodeRow(stage.querySelector('.fs-nodes'), [
            { id: 'fast', name: '前台快模型<div class="muted" style="font-size:11px">倾听 · 应答 · 维持话头</div>' },
            { id: 'slow', name: '后台慢模型<div class="muted" style="font-size:11px">推理 · 规划 · 工具</div>' },
          ], s.st);
          renderMessages(stage.querySelector('.m-msgs'), s.m.map(k => M[k]));
          stage.querySelector('.fs-swap').innerHTML = !s.swap ? '' : `<div class="legend enter" style="margin-top:6px">${pill('acc', '语音通路：级联 / Omni / 全双工')}${pill('acc', '认知架构：快慢分离 / 端到端思考')}<span class="muted" style="font-size:12px">两条轴彼此独立</span></div>`;
        },
      };
    },
  });

  // ───────────────────────── 6.3 视觉定位 ─────────────────────────
  const EL = [
    { id: 'logo', x: 3, y: 6, w: 14, h: 9, t: 'Logo' },
    { id: 'q', x: 20, y: 40, w: 48, h: 11, t: 'Search' },
    { id: 'go', x: 70, y: 40, w: 12, h: 11, t: '搜索' },
    { id: 'gear', x: 92, y: 6, w: 4, h: 7, t: '⚙' },
    { id: 'docs', x: 20, y: 72, w: 16, h: 7, t: 'Docs' },
  ];
  define('grounding', {
    title: '视觉定位：做选择题，还是报坐标',
    ms: 3400,
    scenarios: [
      { id: 'som', label: 'SoM 视觉标注', steps: [
        { marks: {}, caption: '任务：在搜索框里搜“旧金山天气”。模型怎么知道搜索框在哪？' },
        { marks: { logo: 1, q: 2, go: 3, docs: 4 }, caption: '原始 Set-of-Mark：用分割模型在<b>像素上</b>切出候选区域并编号。不需要 DOM，桌面软件、游戏也能用。注意右上角的小齿轮<b>漏检</b>了。' },
        { marks: { logo: 1, q: 2, go: 3, docs: 4 }, pick: 'q', say: '点击 [2]', caption: '模型只需说“点 [2]”，系统换算成该区域的中心坐标去点。<b>选择题比填空题容易</b>。' },
      ] },
      { id: 'dom', label: 'DOM 索引', steps: [
        { marks: { q: 1, go: 2, gear: 3, docs: 4 }, list: true, caption: '结构化元素索引（browser-use 的做法）：从 DOM / 无障碍树里枚举<b>可交互</b>元素并编号，同时给出一份文字列表。Logo 不可交互，不编号；小齿轮按钮也不会漏。' },
        { marks: { q: 1, go: 2, gear: 3, docs: 4 }, list: true, pick: 'q', say: '[1] ← type_text("San Francisco weather")', caption: '模型输出编号，系统用元素中心坐标执行（练习 6.3b 的 <code>index_elements</code>）。不省 token，但定位准确稳定。' },
        { marks: {}, list: false, stale: true, caption: '点“搜索”后页面变了，旧编号全部作废。再用 [2] 只会得到“element 2 no longer exists; call observe again”。<b>每次页面变化都要重新观察</b>。' },
      ] },
      { id: 'coord', label: '坐标预测', steps: [
        { marks: {}, screen: true, caption: '纯坐标预测（SeeClick、Claude computer use）：不标注，模型直接看截图报坐标。真实屏幕 2560×1440。' },
        { marks: {}, screen: true, targets: true, caption: '模型对坐标的理解依赖训练分辨率。<b>按宽高比</b>在三档里选：16:9 的屏幕配 FWXGA 1366×768（1.779 ≈ 1.778）。' },
        { marks: {}, screen: true, targets: true, pick: 'go', cross: [76, 45.5], say: '模型：click(1038, 349) → 屏幕 (1945, 654)', caption: '截图等比缩到 1366×768 送入模型；模型输出的坐标<b>反向映射</b>回真实屏幕再点（练习 6.3a 的 <code>Scaler</code>）。原书例子：(683, 384) → (1280, 720)。' },
        { marks: {}, screen: true, squash: true, cross: [76, 52], say: '硬拉进 1024×768：点偏了', caption: '反例：把 16:9 硬拉进 4:3 的 1024×768，画面被横向压扁，模型的坐标判断<b>系统性偏移</b>。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = `<div class="gr-wrap" style="display:flex;gap:10px;flex-wrap:wrap">
          <div class="gr-screen" style="position:relative;flex:1 1 260px;aspect-ratio:16/9;border:1.5px solid var(--border);border-radius:8px;background:var(--surface);overflow:hidden;transition:transform .4s ease;transform-origin:left center"></div>
          <div class="gr-side" style="flex:1 1 220px;min-width:0;font-size:12.5px"></div></div>
        <div class="gr-say" style="margin-top:6px;min-height:24px"></div>`;
      const screen = stage.querySelector('.gr-screen');
      return {
        render(s) {
          const els = s.stale ? [{ id: 'x', x: 5, y: 10, w: 60, h: 12, t: 'San Francisco weather：70°F，晴' }, { id: 'y', x: 5, y: 30, w: 30, h: 8, t: '首页' }] : EL;
          syncList(screen, [...els, { id: 'cross' }], e => e.id, e => h('div', { style: { position: 'absolute', transition: 'all .35s ease' } }), (el, e) => {
            if (e.id === 'cross') {
              Object.assign(el.style, { display: s.cross ? 'block' : 'none', left: (s.cross || [0])[0] + '%', top: (s.cross || [0, 0])[1] + '%', width: '14px', height: '14px', margin: '-7px 0 0 -7px', borderRadius: '50%', border: `2px solid ${s.squash ? 'var(--bad)' : 'var(--ok)'}`, background: 'transparent', zIndex: 2 });
              return;
            }
            const mark = s.marks[e.id];
            Object.assign(el.style, { left: e.x + '%', top: e.y + '%', width: e.w + '%', height: e.h + '%', border: `1.5px solid ${mark ? 'var(--accent)' : 'var(--border)'}`, borderRadius: '4px', fontSize: '11px', display: 'flex', alignItems: 'center', paddingLeft: '4px', boxSizing: 'border-box', color: 'var(--muted)', background: s.pick === e.id ? 'var(--accent-soft)' : 'transparent', whiteSpace: 'nowrap', overflow: 'visible' });
            el.innerHTML = (mark ? `<span style="position:absolute;top:-9px;left:-6px;background:var(--accent);color:var(--surface);font-size:10px;line-height:14px;padding:0 3px;border-radius:3px">${mark}</span>` : '') + `<span style="overflow:hidden;text-overflow:ellipsis">${esc(e.t)}</span>`;
          });
          screen.style.transform = s.squash ? 'scaleX(0.75)' : 'none';
          let side = '';
          if (s.list) side = `<div class="panel" style="margin:0"><h4>Elements</h4><code style="font-size:11.5px;line-height:1.6;display:block;word-break:break-all">[1] &lt;input type="text" aria-label="Search" /&gt;<br>[2] &lt;button id="go"&gt;搜索&lt;/button&gt;<br>[3] &lt;button aria-label="Settings" /&gt;<br>[4] &lt;a href="/docs"&gt;Docs&lt;/a&gt;</code></div>`;
          else if (s.screen) side = `<div class="panel" style="margin:0"><h4>真实屏幕 2560×1440 · 16:9 = 1.778</h4>${s.targets ? `<div style="line-height:1.9">${pill('', 'XGA 1024×768 · 1.333')}<br>${pill('', 'WXGA 1280×800 · 1.600')}<br>${pill('ok', 'FWXGA 1366×768 · 1.779 ✓')}</div>` : '<span class="muted">模型只见过三种训练分辨率</span>'}${s.squash ? `<div style="margin-top:4px">${pill('bad', '1024×768：横向压扁 25%')}</div>` : ''}</div>`;
          else if (s.stale) side = `<div class="panel" style="margin:0"><h4>旧编号</h4>${pill('bad', 'click(2) → element 2 no longer exists')}</div>`;
          else side = `<div class="muted">${Object.keys(s.marks).length ? '分割模型切出的区域' : '一张没有任何标注的截图'}</div>`;
          stage.querySelector('.gr-side').innerHTML = side;
          stage.querySelector('.gr-say').innerHTML = s.say ? `<span class="pill ${s.squash ? 'bad' : 'acc'}">${esc(s.say)}</span>` : '';
        },
      };
    },
  });

  // ───────────────────────── 6.3 观察接口 ─────────────────────────
  const CO_ROWS = [{ id: 'world', label: '屏幕 / 声音' }, { id: 'obs', label: '观察' }, { id: 'act', label: '动作' }];
  const CO_TICKS = [0, 2, 4, 6, 8, 10].map(v => ({ v, l: v + 's' }));
  define('cu-observe', {
    title: '观察接口：两帧之间发生了什么',
    ms: 3400,
    scenarios: [
      { id: 'static', label: '静态截图', steps: [
        { segs: ['toast', 'voice'], caption: '真实的屏幕会动：1.5 秒时弹出一条转瞬即逝的通知，会议里有人说了一句话。' },
        { segs: ['toast', 'voice', 's0', 's4', 's8'], caption: '传统 Computer Use 每 3–5 秒截一张图、想一步、点一下。<b>两帧之间发生的事</b>它既看不见也听不到。' },
        { segs: ['toast', 'voice', 's0', 's4', 's8', 'a1', 'a2'], ctx: ['c0'], caption: '于是它按旧计划继续操作，错过了通知和会议里的要求。' },
      ] },
      { id: 'aoi', label: '观察接口 AOI', steps: [
        { segs: ['toast', 'voice', 'k0', 'k1'], ctx: ['c1'], caption: '要重新设计的不是动作接口，而是<b>观察接口</b>。一个小模型判断屏幕是否有显著变化，只在变化时截<b>关键帧</b>：通知一出现就截到了。' },
        { segs: ['toast', 'voice', 'k0', 'k1', 'asr'], ctx: ['c1', 'c2'], caption: '音量门控：有声音时才调用语音识别，把文字放进上下文，Agent 就“听到”了。' },
        { segs: ['toast', 'voice', 'k0', 'k1', 'asr', 'k2'], ctx: ['c1d', 'c2', 'c3'], caption: '每张截图再<b>描述成一句话</b>。原图之后被清理出上下文，这句话还在：多模态历史的压缩。' },
      ] },
      { id: 'wm', label: '世界模型', steps: [
        { segs: ['b1', 'b2', 'b3', 'b4'], caption: '观察接口不消除规划延迟：Agent 仍是“截图—思考—点击”串行循环。OSWorld-Human 的研究显示，即使成功，Agent 的步数和等待时间也明显多于人类。' },
        { segs: ['p1', 'p2', 'p3'], caption: '人会先<b>预测</b>动作后果：结果符合预期就沿计划继续，不必每步重新细看。世界模型让 Agent 做同样的“推测执行”：桌面状态 + 动作 → 下一状态。' },
        { segs: ['p1', 'p2x', 'r1'], caption: '实际状态偏离预期（比如弹出确认框）时才停下重新观察和规划。要预测的不是逼真的未来截图，而是<b>可检查的状态差异</b>。' },
      ] },
    ],
    mount(stage) {
      const S = {
        toast: { k: 'toast', row: 'world', from: 1.5, to: 2.7, label: '通知', cls: 'warn' },
        voice: { k: 'voice', row: 'world', from: 5.2, to: 7, label: '“把预算表发群里”', cls: 'warn' },
        s0: { k: 's0', row: 'obs', from: 0, to: 0.4, label: '', cls: 'on' },
        s4: { k: 's4', row: 'obs', from: 4, to: 4.4, label: '', cls: 'on' },
        s8: { k: 's8', row: 'obs', from: 8, to: 8.4, label: '', cls: 'on' },
        a1: { k: 'a1', row: 'act', from: 0.6, to: 3.5, label: '按旧计划操作', cls: 'off' },
        a2: { k: 'a2', row: 'act', from: 4.6, to: 7.6, label: '按旧计划操作', cls: 'off' },
        k0: { k: 'k0', row: 'obs', from: 0, to: 0.4, label: '', cls: 'on' },
        k1: { k: 'k1', row: 'obs', from: 1.5, to: 1.9, label: '帧', cls: 'ok' },
        asr: { k: 'asr', row: 'obs', from: 5.2, to: 7, label: '转写', cls: 'ok' },
        k2: { k: 'k2', row: 'obs', from: 7.2, to: 7.6, label: '帧', cls: 'ok' },
        b1: { k: 'b1', row: 'obs', from: 0, to: 1.5, label: '截图+想', cls: 'on' },
        b2: { k: 'b2', row: 'act', from: 1.5, to: 2.2, label: '点', cls: 'on' },
        b3: { k: 'b3', row: 'obs', from: 2.2, to: 3.7, label: '截图+想', cls: 'on' },
        b4: { k: 'b4', row: 'act', from: 3.7, to: 4.4, label: '点', cls: 'on' },
        p1: { k: 'p1', row: 'obs', from: 0, to: 1.5, label: '截图+预测', cls: 'on' },
        p2: { k: 'p2', row: 'act', from: 1.5, to: 4.5, label: '点 · 输 · 存（与预期一致）', cls: 'ok' },
        p2x: { k: 'p2', row: 'act', from: 1.5, to: 2.6, label: '点 · 输', cls: 'ok' },
        p3: { k: 'p3', row: 'obs', from: 4.5, to: 5, label: '核对', cls: 'ok' },
        r1: { k: 'r1', row: 'obs', from: 2.6, to: 4.1, label: '偏离 → 重新规划', cls: 'bad' },
      };
      const C = {
        c0: { k: 'c0', role: 'status', label: '上下文', html: '截图 ×3（通知和那句话都不在里面）', cls: 'bad' },
        c1: { k: 'c1', role: 'status', label: '上下文', html: '[关键帧 1.5s] 截图' },
        c1d: { k: 'c1', role: 'status', label: '上下文', html: '[关键帧 1.5s] 右下角弹出“会议 10 分钟后开始”', cls: 'good' },
        c2: { k: 'c2', role: 'status', label: '上下文', html: '[语音 5.2s] 王经理：“把预算表发群里”', cls: 'good' },
        c3: { k: 'c3', role: 'status', label: '上下文', html: '[关键帧 7.2s] 截图 + 一句描述' },
      };
      stage.innerHTML = '<div class="co-g"></div><div class="m-msgs" style="margin-top:4px"></div>';
      return {
        render(s) {
          gantt(stage.querySelector('.co-g'), [0, 10], CO_ROWS, s.segs.map(k => S[k]), CO_TICKS);
          renderMessages(stage.querySelector('.m-msgs'), (s.ctx || []).map(k => C[k]));
        },
      };
    },
  });

  // ───────────────────────── 6.3 机器人闭环 ─────────────────────────
  const PLACES = ['table', 'gripper', 'tray', 'bin'];
  const PLACE_NAME = { table: '桌面', gripper: '夹爪', tray: '托盘', bin: '垃圾盒' };
  define('robot-loop', {
    title: '机器人闭环：做完一步，看一眼',
    ms: 3000,
    scenarios: [
      { id: 'open', label: '开环', steps: [
        { at: { cup: 'table', paper: 'table' }, log: [], caption: '原书贯穿的任务：把红色杯子放进托盘，黄色废纸放进垃圾盒，最后确认桌面状态。我们在第一次抓杯子时注入一次瞬时失败。' },
        { at: { cup: 'table', paper: 'table' }, log: [['pick(red_cup)', 'attempted', 'bad']], caption: '开环：一次生成完整动作序列，中途不看。<code>pick</code> 只会返回“已尝试”：执行器不知道自己夹空了。' },
        { at: { cup: 'table', paper: 'table' }, log: [['pick(red_cup)', 'attempted', 'bad'], ['place(red_cup, tray)', 'attempted', 'bad']], caption: '手里是空的，放置也就什么都没发生。' },
        { at: { cup: 'table', paper: 'bin' }, log: [['pick(red_cup)', 'attempted', 'bad'], ['place(red_cup, tray)', 'attempted', 'bad'], ['pick(yellow_paper)', 'attempted'], ['place(yellow_paper, bin)', 'attempted']], claim: 'bad', caption: '4 次调用后它<b>自认为完成了</b>，杯子却还在桌上。一次局部失败被带到了任务末尾。' },
      ] },
      { id: 'closed', label: '逐步检查', steps: [
        { at: { cup: 'table', paper: 'table' }, log: [['pick(red_cup)', 'attempted'], ['observe()', '杯子：桌面 ✗', 'bad']], caption: '同一次注入失败。逐步检查在每个技能后 <code>observe</code>，核对<b>后置条件</b>：pick 之后杯子应该在夹爪里。' },
        { at: { cup: 'gripper', paper: 'table' }, log: [['pick(red_cup)', 'attempted'], ['observe()', '杯子：桌面 ✗', 'bad'], ['pick(red_cup)', '重试'], ['observe()', '杯子：夹爪 ✓', 'ok']], caption: '<b>只重试当前技能</b>，不重做整个计划。' },
        { at: { cup: 'tray', paper: 'bin' }, log: [['…', 'place · pick · place，每步之后都 observe'], ['observe()', '杯子：托盘 ✓ 废纸：垃圾盒 ✓', 'ok']], claim: 'ok', caption: '最后用一次<b>新的观察</b>确认目标，而不是凭“我说过已经完成”（练习 6.3c）。代价是多出的 observe：没有失败时也要 9 次调用，开环只要 4 次。' },
        { at: { cup: 'table', paper: 'table' }, log: [['pick(red_cup)', '失败 ×3', 'bad'], ['stop', '重试用完，不声称完成', 'warn']], caption: '重试有上限。用完了就停下并如实报告，不继续执行后面依赖它的步骤。原书的五个工具里，<code>stop</code> 和 <code>verify_state</code> 一样重要。' },
      ] },
      { id: 'chunk', label: '动作分块', steps: [
        { chunk: 8, moved: null, caption: '大模型每秒只能推理 1–10 次，底层控制要 50–1000 Hz。<b>动作分块</b>：模型一次生成一小段未来动作，控制线程高频回放，模型在后台准备下一段。' },
        { chunk: 8, moved: 2, caption: '执行到第 3 个动作时，杯子被人碰歪了。长分块还在照着旧画面生成的动作走完剩下 5 步。' },
        { chunk: 3, moved: 2, caption: '短分块下一次推理来得更快，能更早看到新画面。代价是运动不够平滑、推理更频繁。分块是<b>平滑性与反应速度</b>之间的取舍，不是没有代价的加速。' },
      ] },
    ],
    mount(stage) {
      stage.innerHTML = '<div class="rl-top"></div><div class="rl-log" style="margin-top:6px"></div><div class="rl-claim" style="margin-top:6px"></div>';
      return {
        render(s) {
          const top = stage.querySelector('.rl-top');
          if (s.chunk) {
            const cells = Array.from({ length: 8 }, (_, i) => {
              const fresh = s.moved == null ? true : i <= s.moved || (s.chunk < 8 && i >= s.chunk);
              const cls = s.moved != null && i > s.moved && !fresh ? 'bad' : i % s.chunk === 0 ? 'on' : 'ok';
              return `<div class="node ${cls}" style="flex:1 1 0;padding:6px 0;font-size:11px">${i % s.chunk === 0 ? '推理' : ''}<br>a${i + 1}</div>`;
            }).join('');
            top.innerHTML = `<div class="muted" style="font-size:12px;margin-bottom:4px">分块长度 ${s.chunk}${s.moved != null ? ` · 第 ${s.moved + 1} 步后杯子被碰歪` : ''}</div><div style="display:flex;gap:4px">${cells}</div>
              <div class="legend" style="margin-top:6px">${pill('acc', '新一次推理')}${pill('ok', '按最新画面执行')}${s.moved != null ? pill('bad', '照旧画面执行') : ''}</div>`;
          } else {
            top.innerHTML = `<div style="display:flex;gap:6px">${PLACES.map(p => {
              const here = Object.entries(s.at).filter(([, v]) => v === p).map(([o]) => o === 'cup' ? '<span style="color:var(--bad)">● 红杯</span>' : '<span style="color:var(--warn)">■ 废纸</span>').join('<br>');
              return `<div class="node ${p === 'gripper' && here ? 'on' : ''}" style="flex:1 1 0;font-size:12.5px;min-height:56px;padding:6px 4px"><span class="muted" style="font-size:11px">${PLACE_NAME[p]}</span><br>${here || '&nbsp;'}</div>`;
            }).join('')}</div>`;
          }
          syncList(stage.querySelector('.rl-log'), s.log || [], (l, i) => i + l[0], () => h('div', { class: 'msg' }), (el, l) => {
            el.className = `msg tool${l[2] === 'bad' ? ' bad' : l[2] === 'ok' ? ' good' : ''}`;
            el.innerHTML = `<span class="role">${esc(l[0])}</span>${esc(l[1])}`;
          });
          stage.querySelector('.rl-claim').innerHTML = !s.claim ? '' : `<div class="legend enter" style="margin:0">${s.claim === 'bad' ? pill('warn', '策略自认为：完成') + pill('bad', '环境事实：杯子还在桌上') : pill('ok', '新观察确认：完成')}</div>`;
        },
      };
    },
  });
})();
