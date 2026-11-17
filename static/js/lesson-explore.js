// Small projected 3D models, drawn locally with no third-party scripts or profile writes.
// Rotation changes the view; dimensions and explanatory text describe the actual model.
window.initLessonExplore = function (subject, topic, pauseLesson, resumeLesson) {
  let kind = null;
  if (subject === "mathematics" && ["volume_area", "solid_geometry"].includes(topic)) kind = "cuboid";
  if (subject === "mathematics" && ["vectors", "analytic_geometry", "matrices_transformations"].includes(topic)) kind = "vector";
  if (subject === "chemistry" && ["chemical_bonding", "organic_chemistry", "organic_chemistry_2", "states_of_matter", "water_and_hydrogen"].includes(topic)) kind = topic === "water_and_hydrogen" ? "water" : "methane";
  if (subject === "computer" && ["intro_computers", "hardware", "data_processing"].includes(topic)) kind = "computer";
  if (subject === "physics" && ["waves_i", "waves_ii", "wave_motion"].includes(topic)) kind = "wave";
  if (subject === "chemistry" && ["separation_techniques", "crude_oil"].includes(topic)) kind = "distillation";
  if (subject === "physics" && ["current_electricity", "simple_electric_circuits"].includes(topic)) kind = "circuit";
  if (!kind) return;
  const root = document.getElementById("lesson-explore");
  const panel = document.getElementById("explore-panel");
  const toggle = document.getElementById("explore-toggle");
  const svg = document.getElementById("explore-svg");
  const angle = document.getElementById("explore-angle");
  const parameter = document.getElementById("explore-parameter");
  const motion = document.getElementById("explore-motion");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  let frame = null, animating = false, previous = 0;
  const descriptions = {
    distillation: ["Distillation: heating and condensation", "A schematic model of simple distillation of salt water. Heating forms water vapour; cooling in the condenser returns it to liquid. Dissolved nonvolatile salt remains in the flask. The apparatus must remain open to avoid pressure buildup. This is a conceptual demonstration, not a practical setup guide."],
    circuit: ["A complete circuit", "A cell, resistor and switch form a closed conducting path when the switch is closed. Opening the switch breaks current. This model does not contain a capacitor and does not demonstrate capacitor discharge."],
    cuboid: ["Cuboid: dimensions, volume and surface area", "A cuboid with length 4 cm, width 3 cm and adjustable height. Rotate to see all three perpendicular dimensions. The diagram is a model; use the given dimensions for calculations."],
    vector: ["A vector in three dimensions", "The arrow goes from O to (3, 2, 2). Rotate the axes to see its components. Rotation changes your view, not the vector or its length. The axes use the same scale."],
    methane: ["Methane: tetrahedral molecular shape", "One carbon is bonded to four hydrogens at the vertices of a tetrahedron, with bond angles about 109.5°. Ball sizes and bond lengths are illustrative. These are bonds, not electron orbits; molecules do not spin in unison."],
    water: ["Water: a bent molecule", "Two hydrogen atoms bond to oxygen at an angle about 104.5°. Two lone pairs on oxygen repel bonding pairs, producing the bent molecular shape. Lone pairs are not drawn. Colours and sizes are illustrative."],
    computer: ["Input, processing and output", "An illustrative data-flow model, not the physical shape of a computer. Input supplies data, the CPU processes instructions, and output presents results. Main memory exchanges data and instructions with the CPU."],
    wave: ["Transverse wave", "Particles oscillate perpendicular to the direction in which the disturbance travels. This schematic is not a trajectory of matter travelling along the wave."],
  };
  root.hidden = false;
  document.getElementById("explore-title").textContent = descriptions[kind][0];
  document.getElementById("explore-description").textContent = descriptions[kind][1];
  document.getElementById("explore-parameter-label").hidden = !["cuboid","distillation","circuit"].includes(kind);
  if (["distillation","circuit"].includes(kind)) {
    document.getElementById("explore-parameter-label").firstChild.textContent = kind === "circuit" ? "Switch (0 open, 1 closed) " : "Heating (0 off, 1 on) ";
    parameter.min = "0"; parameter.max = "1"; parameter.step = "1"; parameter.value = "0";
  }
  function node(name, attrs, text) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
    if (text !== undefined) el.textContent = text;
    svg.appendChild(el); return el;
  }
  function point(v) {
    const a = Number(angle.value) * Math.PI / 180;
    const x = v[0] * Math.cos(a) - v[2] * Math.sin(a);
    const z = v[0] * Math.sin(a) + v[2] * Math.cos(a);
    return [300 + x * 45, 205 - v[1] * 45 + z * 15];
  }
  function line(a, b, color = "#e5c681", width = 3) {
    const p = point(a), q = point(b);
    node("line", {x1:p[0], y1:p[1], x2:q[0], y2:q[1], stroke:color, "stroke-width":width});
  }
  function label(v, text, color = "#fff") { const p = point(v); node("text", {x:p[0]+8,y:p[1]-8,fill:color,"font-size":16}, text); }
  function ball(v, color, text) { const p = point(v); node("circle", {cx:p[0],cy:p[1],r:text === "C" || text === "O" ? 20 : 13, fill:color,stroke:"#fff","stroke-width":1.5}); label(v,text); }
  function draw() {
    svg.replaceChildren();
    const output = document.getElementById("explore-output");
    if (kind === "distillation") {
      const hot = Number(parameter.value) === 1;
      ball([-3,-.5,0],"#559eb0","Salt water");
      line([-3,-.5,0],[-3,1.5,0]); line([-3,1.5,0],[1,.5,0],hot ? "#e5c681" : "#899ba8",7);
      line([1,.5,0],[2,.25,0]); line([2,.25,0],[2,-1,0]); ball([2,-1,0],"#559eb0","Distillate");
      label([-.7,1.8,0],"Cooling water around vapour tube");
      label([-3,-2,0],hot ? "Heat on" : "Heat off");
      output.textContent = hot ? "Water evaporates → vapour travels to the condenser → heat is removed → liquid water collects. Nonvolatile salt stays behind. Water coolant enters the lower end of a condenser jacket." : "Heating off: no sustained boiling is shown. Switch on to follow the separation stages; rotation changes the view.";
    } else if (kind === "circuit") {
      const closed = Number(parameter.value) === 1;
      const a=[-3,1,0],b=[3,1,0],c=[3,-1,0],d=[-3,-1,0];
      line(a,[-.8,1,0]);
      const resistor=[[-.8,1,0],[-.6,1.2,0],[-.3,.8,0],[0,1.2,0],[.3,.8,0],[.6,1.2,0],[.8,1,0]];
      resistor.slice(1).forEach((p,i)=>line(resistor[i],p));
      line([.8,1,0],b);line(b,c);line(c,[.6,-1,0]);line([-.6,-1,0],d);
      line(d,[-3,-.15,0]);line([-3,.15,0],a);
      line([-3.4,.15,0],[-2.6,.15,0],"#fff",4);line([-3.2,-.15,0],[-2.8,-.15,0],"#fff",4);
      line([-.6,-1,0],[.6,closed ? -1 : -.1,0],closed ? "#77ddbb" : "#de6868",5);
      label([-3,1.1,0],"Cell");label([1,1.1,0],"Resistor");
      output.textContent = closed ? "Switch closed: a complete path permits current through the resistor. Energy is transferred from the cell to the resistor." : "Switch open: the broken path prevents sustained current in this simple model.";
    } else if (kind === "cuboid") {
      const h = Number(parameter.value), pts = [];
      for (let x = 0; x < 2; x++) for (let y = 0; y < 2; y++) for (let z = 0; z < 2; z++) pts.push([x*4-2,y*h-h/2,z*3-1.5]);
      for (let i = 0; i < 8; i++) for (const bit of [1,2,4]) if (!(i & bit)) line(pts[i],pts[i|bit]);
      output.textContent = `l = 4 cm, w = 3 cm, h = ${h.toFixed(1)} cm. V = lwh = ${(12*h).toFixed(1)} cm³. A = 2(lw + lh + wh) = ${(24+14*h).toFixed(1)} cm².`;
    } else if (kind === "vector") {
      const origin = [-1.5,-1,-1];
      for (const [end,name] of [[[3,-1,-1],"x"],[[-1.5,3,-1],"y"],[[-1.5,-1,3],"z"]]) { line(origin,end,"#899ba8",2); label(end,name); }
      const end = [1.5,1,1]; line(origin,end,"#77ddbb",5); ball(end,"#77ddbb","P");
      line(origin,[1.5,-1,-1]); line([1.5,-1,-1],[1.5,1,-1]); line([1.5,1,-1],end);
      output.textContent = "OP = (3, 2, 2). |OP| = √(3² + 2² + 2²) = √17 units. The components form perpendicular steps.";
    } else if (kind === "methane" || kind === "water") {
      const center = [0,0,0];
      const atoms = kind === "methane" ? [[1.4,1.4,1.4],[1.4,-1.4,-1.4],[-1.4,1.4,-1.4],[-1.4,-1.4,1.4]] : [[1.9,-1.47,0],[-1.9,-1.47,0]];
      atoms.forEach(v => line(center,v,"#b5cbd4",5));
      ball(center,kind === "water" ? "#de6868" : "#697b8c",kind === "water" ? "O" : "C");
      atoms.forEach(v => ball(v,"#dbe8ee","H"));
      output.textContent = kind === "methane" ? "CH₄ · four bonding pairs · tetrahedral · approximately 109.5°" : "H₂O · two bonding pairs and two lone pairs · bent · approximately 104.5°";
    } else if (kind === "computer") {
      const pts = [[-3,0,0],[0,0,0],[3,0,0],[0,2,0]];
      line(pts[0],pts[1]); line(pts[1],pts[2]); line(pts[1],pts[3]);
      pts.forEach((p,i) => { ball(p,"#537e7c",["Input →","CPU →","Output","Memory ↕"][i]); });
      output.textContent = "Example: keyboard enters 2 + 3 → CPU executes addition using memory → screen displays 5. Lines indicate data exchange, not physical wiring.";
    } else {
      for (let i=0;i<50;i++) line([(i-25)/8,Math.sin(i/5),0],[(i-24)/8,Math.sin((i+1)/5),0],"#77ddbb");
      output.textContent = "Rotate to inspect the transverse displacement; this view shows one instant of the wave.";
    }
  }
  function stop() { animating = false; if(frame !== null) cancelAnimationFrame(frame); frame = null; previous = 0; motion.setAttribute("aria-pressed","false"); motion.textContent = "Animate"; }
  function animate(now) {
    if (!animating || panel.hidden || document.hidden) { stop(); return; }
    if (previous) angle.value = String((Number(angle.value) + Math.min(50,now-previous)*.025)%360);
    previous = now; draw(); frame = requestAnimationFrame(animate);
  }
  function close() { if (panel.hidden) return; stop(); panel.hidden = true; toggle.setAttribute("aria-expanded","false"); toggle.focus(); }
  toggle.addEventListener("click", () => { if (!panel.hidden) { close(); return; } pauseLesson(); panel.hidden = false; toggle.setAttribute("aria-expanded","true"); draw(); angle.focus(); });
  document.getElementById("explore-resume").addEventListener("click", () => { close(); resumeLesson(); });
  angle.addEventListener("input", draw); parameter.addEventListener("input", draw);
  motion.disabled = reduced.matches;
  motion.addEventListener("click", () => { if(animating) { stop(); return; } animating = true; motion.setAttribute("aria-pressed","true"); motion.textContent="Stop animation"; frame=requestAnimationFrame(animate); });
  reduced.addEventListener("change", () => { stop(); motion.disabled = reduced.matches; });
  document.addEventListener("visibilitychange", () => { if(document.hidden) stop(); });
  panel.addEventListener("keydown", e => { if(e.key === "Escape") close(); });
  window.addEventListener("pagehide", stop);
  return {close};
};
