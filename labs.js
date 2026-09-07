/* 确定性的浏览器教学实验，无网络请求、任意代码执行或真实订单操作。 */
window.mountBookLab = function (kind, root, complete) {
  const $ = (s) => root.querySelector(s);
  const on = (s, fn, event = 'click') => $(s).addEventListener(event, fn);
  const feedback = (text, bad = false) => { $('#result').className = `feedback${bad ? ' error' : ''}`; $('#result').textContent = text; };
  const done = (message) => { complete(); if (message) feedback(message); };
  const result = '<div id="result" class="feedback" role="status"></div>';
  const button = (id, label, primary = false) => `<button id="${id}" class="${primary ? 'primary' : 'secondary'}">${label}</button>`;

  if (kind === 'parts') {
    let enabled = [true, true, true]; const observed = new Set(); let ran = false;
    root.innerHTML = `<div class="lab-stage"><h3>任务：杭州周末出行，应该带什么？</h3><div class="control-row">${['LLM 大脑','上下文 眼睛','工具 手脚'].map((n,i)=>`<button class="toggle" data-part="${i}" aria-pressed="true"><i aria-hidden="true"></i>${n}</button>`).join('')}</div>${button('run','运行助理',true)}<p class="hint" id="parts-progress">依次关闭三个零件，观察变化，再恢复全部零件运行。</p></div>${result}`;
    root.querySelectorAll('[data-part]').forEach(b => b.addEventListener('click', () => {
      const i = Number(b.dataset.part); enabled[i] = !enabled[i]; b.setAttribute('aria-pressed', String(enabled[i]));
      if (!enabled[i]) { observed.add(i); feedback(['缺少决策内核：资料和接口都在，但没有模型理解目标并选择下一步。','缺少当前信息：模型看不到用户目标、工具定义和结果，无法可靠判断该做什么。','缺少外部接口：模型可以给一般建议，但无法核实这里要求的天气事实。'][i], true); }
      else feedback('零件已恢复。还要让它们在同一个循环里协作。');
      $('#parts-progress').textContent = `已观察 ${observed.size} / 3 种缺失。${ran ? '已运行完整助理。' : '最后恢复全部零件再运行。'}`;
    }));
    on('#run', () => { if (enabled.some(x=>!x)) { feedback('还有零件缺失。先恢复全部零件，再完成查询与建议。',true); return; }
      ran = true; feedback('模拟轨迹：理解杭州出行目标 → 调用天气工具 → 读取“有雨，18°C” → 建议带伞与薄外套。结果反馈让建议有了依据。');
      if (observed.size === 3) done(); else $('#parts-progress').textContent = `完整助理已运行。再观察剩余 ${3-observed.size} 种零件缺失，并恢复后运行。`;
    });
  }
  if (kind === 'loop') {
    let step=0, retain=true; const finished = new Set();
    const paths = {
      full:['用户目标进入上下文：查杭州天气并给出出行建议。','模型提议：weather({ city: "杭州" })。','运行时执行工具，工具返回：有雨，18°C。','工具结果追加到轨迹，下一轮模型看见“有雨”。','模型给出带伞建议；任务达到本例的验收条件，正常停止。'],
      missing:['用户目标进入上下文：查杭州天气并给出出行建议。','模型提议：weather({ city: "杭州" })。','工具已返回有雨，但结果被移除，没有进入下一轮上下文。','模型缺少结果，再次提出查询（这是教学示例中的一条可能路径）。','达到本例的重试预算，运行时停止。已终止，但任务未成功。']
    };
    root.innerHTML=`<div class="lab-stage"><button id="retain" class="toggle" aria-pressed="true"><i aria-hidden="true"></i>保留工具结果反馈</button><ol class="trace" id="trace"></ol><div class="control-row">${button('advance','推进下一步',true)}${button('restart','重播当前轨迹')}</div><p class="hint" id="loop-count">0 / 5 步 · 两条路径均需走到终点</p></div>${result}`;
    function reset() { step=0; $('#trace').innerHTML=''; $('#advance').disabled=false; $('#loop-count').textContent=`0 / 5 步 · 已观察 ${finished.size} / 2 条路径`; feedback(''); }
    on('#retain',()=>{retain=!retain;$('#retain').setAttribute('aria-pressed',String(retain));reset();});
    on('#restart',reset);
    on('#advance',()=>{const li=document.createElement('li'); const n=document.createElement('span');n.textContent=String(step+1).padStart(2,'0');li.append(n,document.createTextNode(paths[retain?'full':'missing'][step]));$('#trace').append(li);step++;$('#loop-count').textContent=`${step} / 5 步 · 已观察 ${finished.size} / 2 条路径`;
      if(step===5){finished.add(retain);$('#advance').disabled=true;$('#loop-count').textContent=`5 / 5 步 · 已观察 ${finished.size} / 2 条路径`;feedback(retain?'成功路径结束。关闭反馈后，再走一遍，看看结束状态有什么不同。':'缺反馈路径被预算终止：终止并不等于完成目标。');if(finished.size===2)done('两条轨迹都已观察。关键差异是工具结果是否进入下一轮，而不是有没有调用过工具。');}
    });
  }
  if (kind === 'context') {
    const items=[['用户目标：杭州周末出行',15,true],['约束：只查询，不代订',15,true],['最新天气结果及来源',30,true],['重复的长篇闲聊',50,false],['全部历史原始日志',70,false],['当前任务的简短摘要',20,false]];let selected=new Set();
    root.innerHTML=`<div class="lab-stage"><div class="range-label"><span>上下文容量</span><output id="capacity-value">0 / 100</output></div><div class="capacity" id="capacity"><div id="capacity-bar"></div></div><div class="chip-grid">${items.map((x,i)=>`<button class="chip" data-item="${i}" aria-pressed="false">${x[0]}<small>${x[1]} 容量单位</small></button>`).join('')}</div><div class="control-row">${button('check','检查工作桌',true)}</div></div>${result}`;
    const total=()=>[...selected].reduce((v,i)=>v+items[i][1],0);
    root.querySelectorAll('[data-item]').forEach(b=>b.addEventListener('click',()=>{const i=Number(b.dataset.item);selected.has(i)?selected.delete(i):selected.add(i);b.setAttribute('aria-pressed',String(selected.has(i)));$('#capacity-value').textContent=`${total()} / 100`;$('#capacity-bar').style.width=`${Math.min(total(),100)}%`;$('#capacity').classList.toggle('over',total()>100);feedback('');}));
    on('#check',()=>{if(total()>100)feedback('超过预算。尝试移除重复聊天和原始日志，而不是丢掉关键约束。',true);else if([0,1,2].some(i=>!selected.has(i)))feedback('仍缺少目标、授权约束或最新结果。只有节省空间还不够，模型需要足够信息。',true);else done('整理成功：保留目标、授权边界和最新证据，容量仍在预算内。摘要可以保留，但要能追溯来源。');});
  }
  if(kind === 'tools') {
    let blocked=false,authorized=false,executed=false;
    root.innerHTML=`<div class="lab-stage"><pre>cancel_order({ order_id: "DEMO-042" })\n订单：教学示例订单\n用户原始要求：仅查询状态</pre><label class="toggle"><input id="authorized" type="checkbox">模拟用户确认：同意取消 DEMO-042</label><div class="control-row">${button('execute','尝试执行',true)}${button('verify','查询状态并核验')}</div><div class="status-label" id="order-state">执行层：待校验 · 尚未取消</div></div>${result}`;
    on('#authorized',()=>{authorized=$('#authorized').checked;feedback('授权范围已更新，但是否执行仍要由运行时校验。');},'change');
    on('#execute',()=>{if(!authorized){blocked=true;feedback('已拦截：用户只授权查询，没有授权取消。模型提出调用不能代替用户许可。',true);}else{executed=true;$('#order-state').textContent='执行层：模拟调用成功 · 等待结果核验';feedback('模拟取消调用已返回。下一步查询订单状态，验证是否真正取消。');}});
    on('#verify',()=>{if(!executed){feedback('模拟订单状态：有效，尚未执行取消。先完成授权与执行。',true);return;}$('#order-state').textContent='执行层：订单已取消 · 状态核验通过';if(blocked)done('已走完拦截 → 明确授权 → 执行 → 验证。安全边界落实在执行层。');else feedback('已核验取消结果。还需观察未授权分支：取消勾选后再次尝试，确认运行时会拦截，再核验。');});
  }
  if(kind === 'rag') {
    let retrieved=false, choice=null;
    root.innerHTML=`<div class="lab-stage"><h3>问题：差旅住宿每晚最多报销多少？</h3>${button('retrieve','检索教学知识库',true)}<div id="documents" class="answers" style="margin-top:18px"></div><div class="control-row">${button('generate','根据所选证据回答')}</div></div>${result}`;
    on('#retrieve',()=>{retrieved=true;$('#documents').innerHTML=[['差旅政策 · v1 · 已废止','旧标准：每晚 400 元。'],['差旅政策 · v2 · 当前有效','适用于本题员工：每晚最多 500 元。'],['午餐补贴 · 当前有效','每天午餐补贴 30 元，与住宿无关。']].map((x,i)=>`<button class="chip" aria-pressed="false" data-doc="${i}">${x[0]}<small>${x[1]}</small></button>`).join('');choice=null;feedback('找到三条候选。检查相关性、适用范围和时效，再选择一条证据。');root.querySelectorAll('[data-doc]').forEach(b=>b.addEventListener('click',()=>{choice=Number(b.dataset.doc);root.querySelectorAll('[data-doc]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));feedback('证据已选定，点击生成回答。');}));});
    on('#generate',()=>{if(!retrieved||choice===null)feedback('先检索并选择证据。',true);else if(choice===0)feedback('这条政策已废止。虽然关键词匹配，但不能支撑当前标准。',true);else if(choice===2)feedback('这条资料讲午餐补贴，与住宿问题不相关。',true);else done('基于“差旅政策 v2（当前有效）”，本题员工住宿每晚最多报销 500 元。[来源：教学知识库 / 差旅政策 v2] 这是虚构政策，不是实际报销建议。');});
  }
  if(kind === 'code') {
    let fixed=false, sawFailure=false;
    root.innerHTML=`<div class="lab-stage"><p class="hint">规则：金额不超过 500 即可。符号 &lt; 表示“小于”，&lt;= 表示“小于或等于”。</p><pre id="snippet">function canReimburse(amount) {\n  return amount &lt; 500;\n}</pre><div class="control-row">${button('test','运行 3 个边界用例',true)}${button('fix','替换为 ≤')}</div><div id="tests"></div></div>${result}`;
    on('#fix',()=>{fixed=!fixed;$('#snippet').textContent=`function canReimburse(amount) {\n  return amount ${fixed?'<=':'<'} 500;\n}`;$('#fix').textContent=fixed?'还原为 <':'替换为 ≤';$('#tests').innerHTML='';feedback('代码已变更。请重新运行用例，不沿用旧的验证结果。');});
    on('#test',()=>{const inputs=[499,500,501];$('#tests').innerHTML=`<table><thead><tr><th>金额</th><th>预期</th><th>实际</th><th>结论</th></tr></thead><tbody>${inputs.map(v=>{const expected=v<=500;const actual=fixed?v<=500:v<500;return `<tr><td>${v}</td><td>${expected?'通过':'拒绝'}</td><td>${actual?'通过':'拒绝'}</td><td class="${expected===actual?'pass':'fail'}">${expected===actual?'✓ 符合':'✕ 边界错误'}</td></tr>`;}).join('')}</tbody></table>`;if(!fixed){sawFailure=true;feedback('金额正好 500 被错误拒绝了。根据规则，把 < 改成 ≤ 后重新验证。',true);}else if(sawFailure)done('3 / 3 用例符合规则。你完成了发现错误 → 修正 → 再验证的闭环。它只证明当前用例，生产系统还需更多输入校验。');else feedback('3 / 3 用例通过。请还原 < 并运行，先观察失败证据，再修复和验证。');});
  }
  if(kind === 'eval') {
    root.innerHTML=`<div class="lab-stage"><label class="range-label" for="probability">单次成功率 p <output id="p-value">80%</output></label><input id="probability" type="range" min="10" max="100" step="5" value="80"><label class="range-label" for="attempts">尝试次数 k <output id="k-value">3 次</output></label><input id="attempts" type="range" min="1" max="10" value="3"><div class="metric-grid"><div class="metric"><span>至少一次成功</span><strong id="any">99.2%</strong><small>1 − (1 − p)<sup>k</sup></small></div><div class="metric"><span>每次都成功</span><strong id="every">51.2%</strong><small>p<sup>k</sup></small></div></div><p class="hint">假设各次尝试独立、单次成功率固定。这里的 80% 是教学输入，不是实测数据。</p></div>${result}`;
    function update(){const p=Number($('#probability').value)/100,k=Number($('#attempts').value);$('#p-value').textContent=`${Math.round(p*100)}%`;$('#k-value').textContent=`${k} 次`;$('#any').textContent=`${((1-(1-p)**k)*100).toFixed(1)}%`;$('#every').textContent=`${(p**k*100).toFixed(1)}%`;done(k===1?'一次尝试时，两项概率相等。增加次数，观察能力上限与稳定交付的差异。':'同样的单次能力，多次尝试更容易至少成功一次，却更难保证次次成功（p=100% 时两项均为 100%）。');}
    on('#probability',update,'input');on('#attempts',update,'input');
  }
  // 多场景决策共用结构；每题反馈解释原因，不把点击本身当作掌握。
  const decks={
    workflow:[
      ['发票金额校验，规则与顺序明确。',['确定性工作流','自主探索'],0,'固定规则由程序执行更容易验证；无需每次重新规划。'],
      ['服务间歇性故障，根因未知，需要边观察边排查。',['只按固定清单，不允许根据结果调整','带预算与工具边界的 Agent'],1,'探索路径未知时，Agent 可按新证据调整，但仍需预算、验证与停止条件。']
    ],
    evolve:[
      ['产品退款期限变更了。',['更新带版本与来源的知识','只把模型换大'],0,'变化的是事实，先更新知识，并用新旧政策边界案例检查。'],
      ['工具调用顺序总是遗漏必要检查。',['把流程沉淀为 Skill，并验证触发与遵循','保存整段闲聊就结束'],0,'变化的是操作方法，需要可执行的流程说明与回归验收。'],
      ['无论模型怎么说，都不能超出用户授权金额。',['仅让模型记住这条规则','在程序执行层实施硬约束'],1,'确定性的权限边界适合由程序约束，并测试边界金额及越权分支。']
    ],
    training:[
      ['已有大量经过核验的输入输出范例，希望稳定模型输出格式。',['SFT：学习这些示范','RAG：只检索票价'],0,'SFT 是与这个训练目标匹配的方法，但真实项目仍应先做小规模验证。'],
      ['怎样奖励“执行任务”的 Agent？',['输出“已完成”越快奖励越多','完成可验证目标，且满足关键过程约束'],1,'奖励要对齐真正的结果与过程；只奖励结束速度容易鼓励提前退出。']
    ]
  };
  if(decks[kind]) {
    const deck=decks[kind]; let index=0,passed=false;
    root.innerHTML=`<div class="lab-stage"><div class="decision-progress" id="decision-progress"></div><h3 id="scenario"></h3><div class="answers" id="choices"></div><div id="result" class="feedback" role="status"></div><div class="control-row">${button('next-case','下一情境',true)}</div></div>`;
    function render(){passed=false;const x=deck[index];$('#decision-progress').textContent=`情境 ${index+1} / ${deck.length}`;$('#scenario').textContent=x[0];$('#choices').innerHTML=x[1].map((t,i)=>`<button class="answer" data-choice="${i}"><span class="letter">${String.fromCharCode(65+i)}</span>${t}</button>`).join('');$('#next-case').disabled=true;$('#next-case').textContent=index===deck.length-1?'完成情境实验':'下一情境';feedback('');root.querySelectorAll('[data-choice]').forEach(b=>b.addEventListener('click',()=>{if(passed)return;const correct=Number(b.dataset.choice)===x[2];b.classList.add(correct?'correct':'incorrect');feedback(correct?x[3]:'再想一想：'+x[3],!correct);if(correct){passed=true;$('#next-case').disabled=false;}}));}
    on('#next-case',()=>{if(!passed)return;if(index<deck.length-1){index++;render();}else{$('#next-case').disabled=true;done('全部情境已完成。记住：先判断问题发生在哪一层，再选择解决方式。');}});render();
  }
  if(kind === 'vision') {
    let named=false,saved=false,failed=false;
    root.innerHTML=`<div class="lab-stage"><div class="mini-browser"><div class="mini-bar">模拟界面 / travel-plan.local · 不是真实网站</div><div class="mini-content"><strong>周末出行计划</strong><p id="name-state">计划名称：（尚未填写）</p><div class="control-row">${button('name','填写“杭州周末游”')}${button('save','点击保存',true)}</div><div class="mini-status" id="environment">界面当前状态：尚未保存</div></div></div><div class="control-row">${button('screenshot','获取新截图（状态观察）')}</div><div class="mini-status" id="observation">Agent 看到的旧状态：空表单，尚未操作。</div></div>${result}`;
    on('#name',()=>{named=true;$('#name-state').textContent='计划名称：杭州周末游';feedback('输入已经改变，仍需保存并观察新状态。');});
    on('#save',()=>{if(!named){failed=true;$('#environment').textContent='界面当前状态：校验失败，计划名称不能为空';feedback('点击发生了，但保存失败。先获取新截图，读取校验信息，再修正。',true);}else{saved=true;$('#environment').textContent='界面当前状态：保存成功 · 记录 DEMO-001';feedback('环境已更新。Agent 仍需获取新截图，不能只根据点击动作推断成功。');}});
    on('#screenshot',()=>{$('#observation').textContent=`Agent 的最新观察：${$('#environment').textContent.replace('界面当前状态：','')}`;if(saved&&failed)done('新观察确认：保存成功，存在记录 DEMO-001。你用新状态验证了动作结果，也观察了失败路径。');else if(saved)feedback('观察到保存成功。要完成实验，还需看一次失败路径：点击下面重置按钮，再先保存空表单。');else feedback(failed?'观察到了字段校验失败。填写名称后重新保存，再观察新状态。':'当前仍是未保存状态。请先尝试保存空表单，观察失败。',!saved);if(saved&&!failed&&!$('#vision-reset')){const b=document.createElement('button');b.id='vision-reset';b.className='secondary';b.textContent='重置模拟表单';$('#observation').after(b);b.addEventListener('click',()=>{named=false;saved=false;$('#name-state').textContent='计划名称：（尚未填写）';$('#environment').textContent='界面当前状态：尚未保存';$('#observation').textContent='Agent 看到的旧状态：空表单。';b.remove();feedback('已重置，请先点击保存。');});}});
  }
  if(kind === 'team') {
    root.innerHTML=`<div class="lab-stage"><h3>审核者的任务移交包</h3><div class="answers">${[['goal','目标：核对回答是否符合当前公司政策'],['source','证据：最新政策原文与版本信息'],['scope','权限：只读，禁止修改原始文档'],['rubric','验收：引用正确、适用范围一致'],['bias','只提供写作者的“我已经全部验证”声明']].map(x=>`<label class="chip"><input type="checkbox" id="team-${x[0]}"> ${x[1]}</label>`).join('')}</div><div class="control-row">${button('review','启动模拟审查',true)}</div></div>${result}`;
    on('#review',()=>{const needed=['goal','source','scope','rubric'];if(needed.some(x=>!$('#team-'+x).checked))feedback('移交包还缺目标、原始证据、权限边界或验收标准。隔离上下文的审核者不能靠猜测补齐。',true);else if($('#team-bias').checked)feedback('移交中仍包含“只提供自我验证声明”。让审核者直接核对原始证据，避免用声明替代独立验证。',true);else done('模拟审查发现：草稿引用旧政策 v1，而原文是 v2。审核者返回了版本差异、原文证据与修改建议，没有改动原始文档。你设计了一个有信息增量的协作闭环。');});
  }
};
