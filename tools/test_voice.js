// Exercise the real narrator against controlled audio clocks; no speech service calls.
const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
(async () => {
  let pending = null, clip = null;
  const sandbox = {
    window: {}, SERVER_TTS: true, performance: {now: () => 1000},
    setTimeout: () => {}, csrfHeaders: x=>x,
    URL: {createObjectURL: ()=>'blob:fixture',revokeObjectURL:()=>{}},
    fetch: () => new Promise(resolve=> { pending=resolve; }),
    Audio: class {
      constructor(){ this.currentTime=0;this.duration=8;this.played=false;clip=this; }
      play(){this.played=true;if(this.onplaying)this.onplaying();return Promise.resolve();}
      pause(){this.played=false;}
    },
  };
  vm.createContext(sandbox);vm.runInContext(fs.readFileSync('static/js/voice.js','utf8'),sandbox);
  const voice=sandbox.window.Voice;
  voice.speak('A controlled narration line.');
  assert.equal(voice.progress(30),0,'freeze while waiting for synthesis');
  voice.pause();
  pending({ok:true,status:200,blob:async()=>({})});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(clip.played,false,'pausing pending synthesis must also prevent late playback');
  voice.resume();assert.equal(clip.played,true);
  clip.currentTime=2;
  assert.equal(voice.progress(30),.25,'use actual audio length, not the estimated speech duration');
  voice.setRate(1.25);assert.equal(clip.playbackRate,1.25);assert.equal(voice.progress(30),.25);
  voice.pause();assert.equal(clip.played,false);assert.equal(voice.progress(30),.25);
  voice.resume();clip.currentTime=8;clip.onended();assert.equal(voice.isDone(),true);assert.equal(voice.progress(30),1);
  voice.cancel();assert.equal(voice.isDone(),true);
  console.log('PASS audio clock: synthesis wait, pending pause, duration scaling, speed, pause/resume, completion');
})();
