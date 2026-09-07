(() => {
  'use strict';
  const lessons = window.BOOK_LESSONS;
  const KEY = 'agent-book-guide-v1.4-progress';
  const $ = s => document.querySelector(s);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const arrow = '<svg class="arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h15m-6-6 6 6-6 6"/></svg>';
  const blank = () => ({ current:0, step:0, labs:[], answers:{}, notes:{} });
  let state = blank(), storageOK = true, toastTimer;
  try {
    const saved = JSON.parse(localStorage.getItem(KEY));
    if (saved && typeof saved === 'object') {
      state.current = Number.isInteger(saved.current) && saved.current >= 0 && saved.current < lessons.length ? saved.current : 0;
      state.step = [0,1,2].includes(saved.step) ? saved.step : 0;
      state.labs = Array.isArray(saved.labs) ? [...new Set(saved.labs.filter(x => Number.isInteger(x) && x >= 0 && x < lessons.length))] : [];
      lessons.forEach((lesson,i) => {
        if (Array.isArray(saved.answers?.[i])) state.answers[i] = lesson.quiz.map((q,j) => saved.answers[i][j] === q[2] ? q[2] : null);
        if (typeof saved.notes?.[i] === 'string') state.notes[i] = saved.notes[i].slice(0,12000);
      });
    }
  } catch { storageOK = false; }
  const mastered = i => state.labs.includes(i) && lessons[i].quiz.every((q,j) => state.answers[i]?.[j] === q[2]);
  const count = () => lessons.filter((_,i) => mastered(i)).length;
  function toast(message) { $('#toast').textContent = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').textContent = '', 3800); }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { if (storageOK) toast('浏览器无法保存进度，本次学习仍可继续。请导出笔记。'); storageOK = false; } }
  function updateNav() {
    let group='';
    $('#lesson-nav').innerHTML = lessons.map((l,i) => {
      const heading = group !== l.group ? `<p class="nav-group">${l.group}</p>` : ''; group=l.group;
      return `${heading}<button class="lesson-link${i===state.current?' active':''}" data-lesson="${i}" ${i===state.current?'aria-current="step"':''}><span class="num">${String(i+1).padStart(2,'0')}</span><span>${l.title}</span>${mastered(i)?'<span class="done-mark" aria-label="已掌握">✓</span>':''}</button>`;
    }).join('');
    $('#progress-count').textContent = `${count()} / ${lessons.length}`; $('#progress').value = count(); $('#group').textContent = lessons[state.current].group;
    document.querySelectorAll('[data-lesson]').forEach(b => b.addEventListener('click', () => navigate(Number(b.dataset.lesson),0)));
  }
  function navigate(index, step) {
    state.current=index;state.step=step;save();render();$('#sidebar').classList.remove('open');$('#menu').setAttribute('aria-expanded','false');window.scrollTo({top:0,behavior:'instant'});$('#lesson').focus({preventScroll:true});
  }
  function source(l) { return `<div class="source"><span>原书 ${l.source} · 书内第 ${l.pages[0]}–${l.pages[1]} 页</span><a href="source.pdf#page=${l.pages[0]+8}" target="_blank" rel="noopener">回到原书 ↗</a><span>PDF 第 ${l.pages[0]+8} 页起</span></div>`; }
  function footer() {
    const i=state.current;
    if(state.step===0) return `<span>每次只学一个概念。</span><button id="continue" class="primary">进入动手实验 ${arrow}</button>`;
    if(state.step===1) return `<span id="lab-next-hint">${state.labs.includes(i)?'实验已完成，可以检验理解。':'完成本关实验，再检验理解。'}</span><button id="continue" class="primary" ${state.labs.includes(i)?'':'disabled'}>检验我的理解 ${arrow}</button>`;
    if(mastered(i)) return `<span>✓ 已掌握 · 随时可以回来复习</span><button id="continue" class="primary">${i<lessons.length-1?'下一关':'查看学习回顾'} ${arrow}</button>`;
    return `<span>${state.labs.includes(i)?'两题答对后，即可进入下一关。':'请先完成动手实验，再完成两题。'}</span><button id="continue" class="primary" disabled>完成本关 ${arrow}</button>`;
  }
  function render() {
    const l=lessons[state.current];updateNav();
    document.title=`${String(state.current+1).padStart(2,'0')} ${l.title} · Agent 学习实验室`;
    $('#lesson').innerHTML=`<div class="lesson-meta"><span class="index">${String(state.current+1).padStart(2,'0')} / 12</span><span>学习约 ${l.minutes} 分钟${mastered(state.current)?' · 已掌握':''}</span></div><h1>${l.heading}</h1><p class="intro">${l.intro}</p><div class="steps" role="tablist" aria-label="学习步骤">${['理解概念','动手实验','检验理解'].map((s,i)=>`<button id="step-${i}" role="tab" aria-selected="${state.step===i}" aria-controls="stage" class="step${state.step===i?' active':''}" data-step="${i}" tabindex="${state.step===i?0:-1}"><span class="step-number">0${i+1}</span>${s}</button>`).join('')}</div><section id="stage" role="tabpanel" aria-labelledby="step-${state.step}" class="panel"></section>${source(l)}<div class="bottom-nav" id="bottom-nav">${footer()}</div>`;
    document.querySelectorAll('[data-step]').forEach(b=>{b.addEventListener('click',()=>navigate(state.current,Number(b.dataset.step)));b.addEventListener('keydown',e=>{let step=Number(b.dataset.step);if(e.key==='ArrowRight')step=(step+1)%3;else if(e.key==='ArrowLeft')step=(step+2)%3;else if(e.key==='Home')step=0;else if(e.key==='End')step=2;else return;e.preventDefault();navigate(state.current,step);$(`#step-${step}`).focus();});});
    if(state.step===0) renderConcept(l);
    if(state.step===1) renderLab(l);
    if(state.step===2) renderQuiz(l);
    bindContinue();
  }
  function bindContinue() { $('#continue').addEventListener('click',()=>{if(state.step<2)navigate(state.current,state.step+1);else if(state.current<lessons.length-1)navigate(state.current+1,0);else showRecap();}); }
  function renderConcept(l) {
    $('#stage').innerHTML=`<div class="story"><h2>${l.story}</h2><p>${l.body}</p></div><div class="nodes">${l.nodes.map((n,i)=>`${i?arrow:''}<div class="node"><span class="node-icon" aria-hidden="true">${['01','02','03'][i]}</span><strong>${n[0]}</strong><small>${n[1]}</small></div>`).join('')}</div><div class="takeaway">${l.takeaway}</div><p class="detail">${l.detail}</p>`;
  }
  function renderLab(l) {
    const lessonId=state.current;
    $('#stage').innerHTML=`<div class="lab-kicker"><span>动手实验 · 本地教学模拟</span><span id="lab-status" class="${state.labs.includes(lessonId)?'ok':''}">${state.labs.includes(lessonId)?'✓ 已完成，可重做':'等待你的操作'}</span></div><h2>${l.labTitle}</h2><p class="lab-description">${l.labIntro}</p><div id="lab-root"></div>`;
    window.mountBookLab(l.lab,$('#lab-root'),()=>{
      if(!state.labs.includes(lessonId)){state.labs.push(lessonId);save();}
      $('#lab-status').textContent='✓ 实验已完成';$('#lab-status').className='ok';$('#continue').disabled=false;$('#lab-next-hint').textContent='实验已完成，可以检验理解。';updateNav();
    });
  }
  function renderQuiz(l) {
    const i=state.current;
    if(!state.answers[i])state.answers[i]=[null,null];
    $('#stage').innerHTML=`<div class="lab-kicker"><span>检验理解 · 可以重试，不计时</span><span>答对 ${l.quiz.filter((q,j)=>state.answers[i][j]===q[2]).length} / 2</span></div>${!state.labs.includes(i)?'<div class="feedback">你可以先尝试回答；关卡掌握还需要完成动手实验。</div>':''}${l.quiz.map((q,j)=>`<article class="quiz-card"><div class="question-index">问题 0${j+1}</div><h2 class="question-title">${q[0]}</h2><div class="answers" role="group" aria-label="问题 ${j+1} 选项">${q[1].map((a,k)=>`<button class="answer${state.answers[i][j]===k?' correct':''}" data-q="${j}" data-answer="${k}" ${state.answers[i][j]===q[2]?'disabled':''}><span class="letter">${String.fromCharCode(65+k)}</span>${a}</button>`).join('')}</div><div id="feedback-${j}" class="feedback" role="status">${state.answers[i][j]===q[2]?'✓ 回答正确。'+q[3]:''}</div></article>`).join('')}<div class="reflection"><label for="reflection">用自己的话说一次 <span class="hint">· 选填</span></label><p>${l.reflection}</p><textarea id="reflection" maxlength="12000" placeholder="不用标准答案，写下你现在的理解……">${escape(state.notes[i]||'')}</textarea><p class="hint" id="save-state">${storageOK?'笔记仅保存在当前浏览器，可从右上角导出。':'当前浏览器无法持久保存，请从右上角导出笔记。'}</p></div>`;
    document.querySelectorAll('[data-q]').forEach(b=>b.addEventListener('click',()=>{
      const j=Number(b.dataset.q),a=Number(b.dataset.answer),q=l.quiz[j],correct=a===q[2];
      b.classList.add(correct?'correct':'incorrect');const f=$(`#feedback-${j}`);f.className=`feedback${correct?'':' error'}`;f.textContent=correct?'✓ 回答正确。'+q[3]:'还差一点。'+q[3]+' 再选一次试试。';
      if(correct){state.answers[i][j]=a;save();document.querySelectorAll(`[data-q="${j}"]`).forEach(x=>x.disabled=true);$('#stage .lab-kicker span:last-child').textContent=`答对 ${l.quiz.filter((x,k)=>state.answers[i][k]===x[2]).length} / 2`;updateNav();$('#bottom-nav').innerHTML=footer();bindContinue();}
    }));
    $('#reflection').addEventListener('input',()=>{state.notes[i]=$('#reflection').value;save();$('#save-state').textContent=storageOK?'✓ 已保存到当前浏览器':'当前无法自动保存，请导出笔记。';});
  }
  function openDialog(title,html) { $('#dialog-title').textContent=title;$('#dialog-content').innerHTML=html;if(!$('#drawer').open)$('#drawer').showModal(); }
  function showGlossary() {
    openDialog('术语手册','<label for="term-search" class="hint">搜索中文或英文术语</label><input class="glossary-search" type="search" id="term-search" placeholder="试试：上下文、RAG、Harness"><div id="terms"></div>');
    const renderTerms=()=>{const term=$('#term-search').value.trim().toLowerCase();const list=window.BOOK_GLOSSARY.filter(x=>x.join(' ').toLowerCase().includes(term));$('#terms').innerHTML=list.length?list.map(x=>`<div class="term"><strong>${x[0]}</strong><p>${x[1]}</p></div>`).join(''):'<p>没有找到这个词，试试中文名称或英文缩写。</p>';};
    $('#term-search').addEventListener('input',renderTerms);renderTerms();$('#term-search').focus();
  }
  function exportNotes() {
    const contents=['# 《深入理解 AI Agent》学习笔记','',`已掌握 ${count()} / 12 关`,'基于李博杰著 v1.4（2026-08-13）；导读与本地教学模拟，不是实测模型结果。','',...lessons.flatMap((l,i)=>[`## ${i+1}. ${l.title} ${mastered(i)?'✓ 已掌握':'待完成'}`,`原书 ${l.source}，书内第 ${l.pages[0]}–${l.pages[1]} 页（PDF 页码 +8）。`,'',l.takeaway,'',`回想：${l.reflection}`,'',state.notes[i]||'（尚未记录）',''])].join('\n');
    const url=URL.createObjectURL(new Blob([contents],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='AI-Agent-学习笔记.md';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);toast('学习笔记已导出为 Markdown 文件。');
  }
  function showNotes() {
    const saved=lessons.flatMap((l,i)=>state.notes[i]?.trim()?[`<section class="note-entry"><h3>${String(i+1).padStart(2,'0')} ${l.title}</h3><p>${escape(state.notes[i])}</p><button class="secondary" data-note-go="${i}">返回修改</button></section>`]:[]);
    openDialog('我的学习笔记',`<p class="hint">已掌握 ${count()} / 12 关 · ${storageOK?'保存在当前浏览器':'当前无法持久保存'}</p><button class="primary" id="export">导出笔记 .md</button>${saved.length?saved.join(''):'<p>还没有笔记。在每关「检验理解」底部，用自己的话记录一个想法，就会出现在这里。</p>'}`);
    $('#export').addEventListener('click',exportNotes);document.querySelectorAll('[data-note-go]').forEach(b=>b.addEventListener('click',()=>{$('#drawer').close();navigate(Number(b.dataset.noteGo),2);$('#reflection').focus();}));
  }
  function showRecap() {
    const total=count();
    openDialog(total===12?'你已走完整条学习路径':'学习回顾',`<div class="finish"><h2>${total} / 12 关已掌握</h2><p>${total===12?'你已经从三个零件，走到能判断反馈、上下文、工具边界与协作价值。接下来用一个真实小项目验证理解。':'已完成的关卡会保留。继续补齐动手实验与两道测验，再把这些概念连成一个系统。'}</p></div><button id="export" class="primary">导出我的学习笔记</button><div class="terms">${lessons.map((l,i)=>`<div class="term"><strong>${mastered(i)?'✓':'○'} ${i+1}. ${l.title}</strong><p>${l.takeaway}</p><button class="plain" data-review="${i}">${mastered(i)?'复习这一关':'继续这一关'}</button></div>`).join('')}</div>`);
    $('#export').addEventListener('click',exportNotes);document.querySelectorAll('[data-review]').forEach(b=>b.addEventListener('click',()=>{$('#drawer').close();navigate(Number(b.dataset.review),0);}));
  }
  function showAbout() {
    openDialog('关于这份导读',`<p>来源：李博杰《深入理解 AI Agent：设计原理与工程实践》，v1.4，2026 年 8 月 13 日。本导读对应的 v1.4 PDF 共 307 页、10 章。</p><p>这是基于原书改编的独立互动导读，并非作者官方课程。原书及本项目采用 <a href="LICENSE" target="_blank" rel="noopener">Apache-2.0</a> 许可；<a href="https://github.com/bojieli/ai-agent-book" target="_blank" rel="noopener">原书源码与新版内容</a>由李博杰及原项目贡献者维护。详见 <a href="NOTICE" target="_blank" rel="noopener">版权与改编声明</a>。</p><p>本导读用 12 个关卡重排核心知识。第 1、2、8 关拆解第 1 章；其余关卡覆盖第 2–10 章。第 7、9 章的训练与多模态以概念理解为主，不包含原书全部高级实验或数学推导。</p><p>所有天气、政策、订单、代码测试场景均为确定性的本地教学演示。没有连接真实大模型、天气服务或企业系统，不代表原书实验已被复现。</p><p>原书印刷页码与 PDF 页码相差 8 页；每关链接已加偏移。部分浏览器的内置 PDF 阅读器可能不支持自动跳页，可按标示的 PDF 页码手动定位。</p><p>进度与笔记仅保存到当前浏览器，清理浏览器数据或更换访问地址会影响读取。建议导出重要笔记。</p><div class="control-row"><a class="secondary" href="source.pdf" target="_blank" rel="noopener">打开原书 PDF ↗</a><button id="recap" class="secondary">学习回顾</button></div>`);
    $('#recap').addEventListener('click',showRecap);
  }
  $('#menu').addEventListener('click',()=>{const visible=$('#sidebar').classList.toggle('open');$('#menu').setAttribute('aria-expanded',String(visible));});
  $('#glossary-open').addEventListener('click',showGlossary);$('#notes-open').addEventListener('click',showNotes);$('#about-open').addEventListener('click',showAbout);$('#dialog-close').addEventListener('click',()=>$('#drawer').close());
  $('#drawer').addEventListener('click',e=>{if(e.target===$('#drawer')){const r=$('#drawer').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('#drawer').close();}});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){$('#sidebar').classList.remove('open');$('#menu').setAttribute('aria-expanded','false');}});
  render();if(!storageOK)toast('自动保存暂不可用；可以继续学习并导出笔记。');
})();
