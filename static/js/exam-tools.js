// Local calculator and pointer-based working: no handwriting service is required.
window.examCalculation = function (source) {
  const text=String(source).replace(/×/g,'*').replace(/÷/g,'/').replace(/π/g,'pi').replace(/−/g,'-');
  const tokens=text.match(/(?:\d*\.\d+|\d+\.?\d*)(?:e[+-]?\d+)?|[a-z]+|[()+\-*/^]/gi)||[];
  if(tokens.join('')!==text.replace(/\s/g,'')) throw Error('Use numbers and calculator symbols.');
  let at=0;
  function atom(){
    const t=tokens[at++];
    if(t==='('){const v=sum();if(tokens[at++]!==')')throw Error('Close the bracket.');return v;}
    if(t==='pi')return Math.PI;
    if(['sin','cos','tan','asin','acos','atan','sqrt','log','ln','abs'].includes(t)){
      if(tokens[at++]!=='(')throw Error('Use function(value).');const v=sum();if(tokens[at++]!==')')throw Error('Close the bracket.');
      return ({sin:x=>Math.sin(x*Math.PI/180),cos:x=>Math.cos(x*Math.PI/180),tan:x=>Math.tan(x*Math.PI/180),asin:x=>Math.asin(x)*180/Math.PI,acos:x=>Math.acos(x)*180/Math.PI,atan:x=>Math.atan(x)*180/Math.PI,sqrt:Math.sqrt,log:Math.log10,ln:Math.log,abs:Math.abs})[t](v);
    }
    if(t==null||!/^\d|^\./.test(t))throw Error('Enter a number.');return Number(t);
  }
  function power(){let v=atom();if(tokens[at]==='^'){at++;v=v**unary();}return v;}
  function unary(){if(tokens[at]==='+'){at++;return unary();}if(tokens[at]==='-'){at++;return -unary();}return power();}
  function product(){let v=unary();while(['*','/'].includes(tokens[at])){const op=tokens[at++],r=unary();v=op==='*'?v*r:v/r;}return v;}
  function sum(){let v=product();while(['+','-'].includes(tokens[at])){const op=tokens[at++],r=product();v=op==='+'?v+r:v-r;}return v;}
  const result=sum();if(at!==tokens.length||!Number.isFinite(result))throw Error('Check the calculation.');return Number(result.toPrecision(12));
};
window.examNeedsPad = (subject, question) => subject==='mathematics' || /\b(draw|sketch|plot|construct)\b/i.test(question) || (subject==='physics' && /\b(calculate|determine|compute|evaluate|find|work out)\b/i.test(question));
window.addExamTools = function(slot, stored, onChange) {
  let strokes=Array.isArray(stored.strokes)?structuredClone(stored.strokes):[];
  let active=null, mode='pen', labelField=null;
  const wrap=document.createElement('section');wrap.className='working-tools';
  wrap.innerHTML='<div class="ink-toolbar" role="group" aria-label="Drawing tools"><button type="button" data-tool="pen" aria-pressed="true">Pen</button><button type="button" data-tool="line">Line</button><button type="button" data-tool="rectangle">Box</button><button type="button" data-tool="circle">Circle</button><button type="button" data-tool="label">Label</button><button type="button" data-tool="expand">Expand</button><button type="button" data-tool="undo">Undo</button><button type="button" data-tool="clear">Clear drawing</button><label>Ink <select aria-label="Pen width"><option value="3">Fine</option><option value="5" selected>Medium</option><option value="8">Bold</option></select></label></div><input class="ink-label" aria-label="Diagram label" placeholder="Type a label, then tap the drawing to place it" hidden><canvas width="1000" height="600" class="answer-canvas" aria-label="Draw your working with a mouse, finger or stylus"></canvas><p class="ink-hint">Draw your working here, or use the text box. Line and shape tools keep mouse drawings neat. Both are sent for marking.</p><div class="equation-keys" aria-label="Equation shortcuts"></div>';
  slot.append(wrap);const canvas=wrap.querySelector('canvas'),ctx=canvas.getContext('2d');labelField=wrap.querySelector('.ink-label');
  function draw(){
    ctx.fillStyle='#fffdf8';ctx.fillRect(0,0,1000,600);ctx.strokeStyle='#14233b';ctx.fillStyle='#14233b';ctx.lineCap='round';ctx.lineJoin='round';
    for(const s of strokes.concat(active?[active]:[])){
      ctx.lineWidth=s.width||5;const a=s.points[0],b=s.points[s.points.length-1];ctx.beginPath();
      if(s.mode==='label'){ctx.font='24px sans-serif';ctx.fillText(s.text,a[0],a[1]);continue;}
      if(s.mode==='rectangle')ctx.rect(a[0],a[1],b[0]-a[0],b[1]-a[1]);
      else if(s.mode==='circle')ctx.ellipse((a[0]+b[0])/2,(a[1]+b[1])/2,Math.max(1,Math.abs(b[0]-a[0])/2),Math.max(1,Math.abs(b[1]-a[1])/2),0,0,Math.PI*2);
      else{ctx.moveTo(...a);for(const p of (s.mode==='line'?[b]:s.points.slice(1)))ctx.lineTo(...p);if(s.points.length===1)ctx.lineTo(a[0]+.2,a[1]+.2);}
      ctx.stroke();
    }
  }
  function changed(){draw();onChange();}
  wrap.querySelectorAll('[data-tool]').forEach(btn=>btn.onclick=()=>{
    const next=btn.dataset.tool;if(next==='expand'){const on=wrap.classList.toggle('expanded');btn.textContent=on?'Done drawing':'Expand';btn.setAttribute('aria-expanded',String(on));return;}if(next==='undo'){strokes.pop();changed();return;}if(next==='clear'){strokes=[];changed();return;}
    mode=next;labelField.hidden=mode!=='label';wrap.querySelectorAll('[data-tool]').forEach(b=>b.setAttribute('aria-pressed',String(b===btn)));if(mode==='label')labelField.focus();
  });
  const point=e=>{const r=canvas.getBoundingClientRect();return [Math.max(0,Math.min(1000,(e.clientX-r.left)*1000/r.width)),Math.max(0,Math.min(600,(e.clientY-r.top)*600/r.height))];};
  canvas.onpointerdown=e=>{if(active)return;e.preventDefault();canvas.setPointerCapture(e.pointerId);active={mode,points:[point(e)],width:Number(wrap.querySelector('select').value)};if(mode==='label'){if(labelField.value.trim()){active.text=labelField.value.trim().slice(0,80);strokes.push(active);}active=null;changed();}else draw();};
  canvas.onpointermove=e=>{if(!active)return;e.preventDefault();if(active.points.length<5000)active.points.push(point(e));draw();};
  function finish(){if(active){strokes.push(active);active=null;changed();}}
  canvas.onpointerup=finish;canvas.onpointercancel=finish;
  let target=slot.querySelector('textarea');
  slot.querySelectorAll('textarea,input:not(.ink-label)').forEach(el=>el.addEventListener('focus',()=>target=el));
  for(const [name,value] of [['Fraction','()/()'],['Power','^()'],['Square','²'],['Root','√()'],['×','×'],['÷','÷'],['π','π'],['θ','θ'],['=','='],['±','±'],['New step','\n']]){
    const btn=document.createElement('button');btn.type='button';btn.textContent=name;btn.onmousedown=e=>e.preventDefault();btn.onclick=()=>{if(!target)return;target.setRangeText(value,target.selectionStart,target.selectionEnd,'end');target.dispatchEvent(new Event('input',{bubbles:true}));target.focus();};wrap.querySelector('.equation-keys').append(btn);
  }
  draw();return {snapshot:()=>({strokes, image:strokes.length?canvas.toDataURL('image/png'):''})};
};
document.addEventListener('DOMContentLoaded',()=>{
  if(!['physics','mathematics'].includes(SUBJECT))return;
  const host=document.createElement('details');host.className='exam-calculator';host.innerHTML='<summary>Calculator <span>DEG</span></summary><label>Calculation <input class="calc-expression" inputmode="decimal" placeholder="e.g. 12 × sin(30)"></label><div class="calc-keys"></div><output aria-live="polite"></output>';
  document.querySelector('.exam-stage').prepend(host);const input=host.querySelector('input'),output=host.querySelector('output');
  function calculate(){try{output.textContent=String(examCalculation(input.value));}catch(e){output.textContent=e.message;}}
  for(const key of ['7','8','9','÷','sin(','4','5','6','×','cos(','1','2','3','−','tan(','0','.','π','+','sqrt(','(',')','^','log(','=','asin(','acos(','atan(','⌫','Clear']){
    const b=document.createElement('button');b.type='button';b.textContent=key;b.onclick=()=>{if(key==='='){calculate();return;}if(key==='Clear')input.value='';else if(key==='⌫')input.value=input.value.slice(0,-1);else input.setRangeText(key,input.selectionStart,input.selectionEnd,'end');input.focus();};host.querySelector('.calc-keys').append(b);
  }
  input.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();calculate();}};
});
