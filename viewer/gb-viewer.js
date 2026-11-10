// GateBook 3D viewer core (three.js r160, ES modules)
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

export const PART_LABELS = {
  base: '收纳主体（书页）', table: '旋转桌板（书封）', panel_l: '左侧板腿（封底·左）', panel_r: '右侧板腿（封底·右）',
  hinge_pin: '铰链销（直销，无螺纹）', ring2: '杯架套环 A', ring3: '杯架套环 B', ring4: '杯架底环 C',
  pin: '桌板销轴（卡扣式）', hook_mini: '小双钩', tube_hook: '拉杆挂钩', strap: 'TPU 系留带', buckle: '带扣',
};

const PALETTE = {
  paper: 0xe4e1da, graphite: 0x2b2e34, signal: 0xe3a100,
  alu: 0xb9bec6, shell: 0x5d6873, rubber: 0x1d1f22, band: 0x30343a,
};
const PART_COLOR = {
  base: 'paper', table: 'graphite', panel_l: 'graphite', panel_r: 'graphite', hinge_pin: 'graphite',
  ring2: 'paper', ring3: 'paper', ring4: 'paper', pin: 'graphite', hook_mini: 'graphite', tube_hook: 'graphite', buckle: 'graphite',
};

function mat4(rows) {
  const m = new THREE.Matrix4();
  m.set(...rows[0], ...rows[1], ...rows[2], ...rows[3]);
  return m;
}
function rzAbout(deg, cx, cy) {
  const a = THREE.MathUtils.degToRad(deg);
  const t1 = new THREE.Matrix4().makeTranslation(cx, cy, 0);
  const r = new THREE.Matrix4().makeRotationZ(a);
  const t2 = new THREE.Matrix4().makeTranslation(-cx, -cy, 0);
  return t1.multiply(r).multiply(t2);
}

export async function createViewer(container, opts) {
  const { glbUrl, statesUrl, preserve = false } = opts;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: preserve });
  renderer.setPixelRatio(opts.pixelRatio || Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.92;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;

  const camera = new THREE.PerspectiveCamera(30, 1, 5, 20000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;

  // CAD frame is Z-up, millimetres
  const root = new THREE.Group();
  root.rotation.x = -Math.PI / 2;
  scene.add(root);

  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(-500, 900, 700);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -500, right: 500, top: 500, bottom: -500, near: 10, far: 3000 });
  key.shadow.bias = -0.0004;
  key.shadow.radius = 4;
  scene.add(key);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f99, 0.35));

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(8000, 8000), new THREE.ShadowMaterial({ opacity: 0.18 }));
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const [gltf, states] = await Promise.all([
    new GLTFLoader().loadAsync(glbUrl),
    fetch(statesUrl).then(r => r.json()),
  ]);

  const mats = {
    paper: new THREE.MeshPhysicalMaterial({ color: PALETTE.paper, roughness: 0.5, clearcoat: 0.15, clearcoatRoughness: 0.6 }),
    graphite: new THREE.MeshPhysicalMaterial({ color: PALETTE.graphite, roughness: 0.42, clearcoat: 0.25, clearcoatRoughness: 0.5 }),
    signal: new THREE.MeshStandardMaterial({ color: PALETTE.signal, roughness: 0.8 }),
    alu: new THREE.MeshStandardMaterial({ color: PALETTE.alu, metalness: 0.85, roughness: 0.32 }),
    shell: new THREE.MeshPhysicalMaterial({ color: PALETTE.shell, roughness: 0.28, clearcoat: 0.6 }),
    rubber: new THREE.MeshStandardMaterial({ color: PALETTE.rubber, roughness: 0.9 }),
    band: new THREE.MeshStandardMaterial({ color: PALETTE.band, roughness: 0.95 }),
  };
  const ctxMat = { tube: mats.alu, grip: mats.rubber, suitcase: mats.shell, bands: mats.band };

  // geometry by name
  const geoms = {};
  gltf.scene.traverse(o => { if (o.isMesh) geoms[o.name] = o.geometry; });
  for (const g of Object.values(geoms)) g.computeVertexNormals();

  const parts = {};      // name -> { instances: [Group], meshes }
  const partNames = Object.keys(PART_LABELS);
  const maxInst = n => Math.max(...['use', 'book', 'exploded'].map(s => (states[s][n] || []).length), 1);
  for (const n of partNames) {
    const inst = [];
    for (let i = 0; i < maxInst(n); i++) {
      const grp = new THREE.Group();
      grp.matrixAutoUpdate = true;
      grp.userData.part = n;
      for (const matName of ['petg', 'tpu']) {
        const g = geoms[`${n}__${matName}`];
        if (!g) continue;
        const m = new THREE.Mesh(g, matName === 'tpu' ? mats.signal : mats[PART_COLOR[n]]);
        m.castShadow = true; m.receiveShadow = true;
        m.userData.part = n;
        grp.add(m);
      }
      root.add(grp);
      inst.push(grp);
    }
    parts[n] = { instances: inst };
  }
  const ctx = new THREE.Group();
  root.add(ctx);
  for (const k of ['tube', 'grip', 'suitcase', 'bands']) {
    if (!geoms[`ctx__${k}`]) continue;
    const m = new THREE.Mesh(geoms[`ctx__${k}`], ctxMat[k]);
    m.castShadow = k !== 'suitcase'; m.receiveShadow = true;
    if (k === 'bands') m.userData.mountOnly = true;
    ctx.add(m);
  }

  // ---------- props: coffee cup, phone, boarding pass ----------
  const props = new THREE.Group();
  root.add(props);
  const meta = states.meta;
  {
    const cupMat = new THREE.MeshStandardMaterial({ color: 0xf4f1ec, roughness: 0.7 });
    const sleeveMat = new THREE.MeshStandardMaterial({ color: 0x7a5a43, roughness: 0.9 });
    const lidMat = new THREE.MeshStandardMaterial({ color: 0xf8f8f6, roughness: 0.4 });
    const h = 112;
    const cup = new THREE.Mesh(new THREE.CylinderGeometry(45, 30, h, 48, 1, true), cupMat);
    cup.rotation.x = Math.PI / 2;
    const sleeve = new THREE.Mesh(new THREE.CylinderGeometry(42.6, 37.2, 45, 48, 1, true), sleeveMat);
    sleeve.rotation.x = Math.PI / 2; sleeve.position.z = 8;
    const lid = new THREE.Mesh(new THREE.CylinderGeometry(46.5, 46.5, 7, 48), lidMat);
    lid.rotation.x = Math.PI / 2; lid.position.z = h / 2 + 3;
    const bottom = new THREE.Mesh(new THREE.CircleGeometry(30, 32), cupMat);
    bottom.position.z = -h / 2; bottom.rotation.x = Math.PI;
    const c = new THREE.Group(); c.add(cup, sleeve, lid, bottom);
    // a 90/60 mm tapered paper cup comes to rest on the top rim of ring C (ID 61.1 mm)
    c.position.set(meta.cup[0], meta.cup[1], -30.5 + h / 2);
    c.traverse(o => { if (o.isMesh) { o.castShadow = true; o.material.side = THREE.DoubleSide; } });
    c.userData.prop = 'cup';
    props.add(c);

    const phoneMat = new THREE.MeshPhysicalMaterial({ color: 0x15171b, roughness: 0.25, clearcoat: 1 });
    const screenMat = new THREE.MeshStandardMaterial({ color: 0x23466b, roughness: 0.15, emissive: 0x0d2238, emissiveIntensity: 0.6 });
    const phone = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(8.5, 74, 152), phoneMat);
    const scr = new THREE.Mesh(new THREE.PlaneGeometry(146, 70), screenMat);
    scr.rotation.y = Math.PI / 2; scr.position.x = 4.3;
    const bump = new THREE.Mesh(new THREE.BoxGeometry(2, 26, 26), phoneMat);
    bump.position.set(-5, 18, 52);
    phone.add(body, scr, bump);
    const lean = THREE.MathUtils.degToRad(15);
    phone.rotation.y = -lean;
    phone.position.set(23.9 - 76 * Math.sin(lean), 105, 6.6 + 76 * Math.cos(lean));
    phone.traverse(o => { if (o.isMesh) o.castShadow = true; });
    phone.userData.prop = 'phone';
    props.add(phone);
  }
  // boarding pass: child of the table instance so it swings with it
  const passTex = (() => {
    const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 412;
    const g = cv.getContext('2d');
    g.fillStyle = '#fbfaf7'; g.fillRect(0, 0, 1024, 412);
    g.fillStyle = '#1f6fb2'; g.fillRect(0, 0, 1024, 70);
    g.fillStyle = '#fff'; g.font = 'bold 40px sans-serif'; g.fillText('BOARDING PASS  登机牌', 30, 50);
    g.fillStyle = '#222'; g.font = 'bold 64px monospace'; g.fillText('SIN → PVG', 30, 170);
    g.font = '36px monospace'; g.fillText('GATE B7   SEAT 32A   08:45', 30, 240);
    for (let i = 0; i < 60; i++) { g.fillRect(760 + i * 4, 290, (i % 3) + 1, 90); }
    g.fillStyle = '#1f6fb2'; g.fillRect(720, 70, 6, 342);
    const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
  })();
  const pass = new THREE.Mesh(new THREE.BoxGeometry(203, 82, 0.3),
    [0, 0, 0, 0, 1, 1].map(i => i ? new THREE.MeshStandardMaterial({ map: passTex, roughness: 0.6 }) : new THREE.MeshStandardMaterial({ color: 0xf6f5f2 })));
  // sleeve: X 24..211.5, Y 30..118, z 26.4..28.6 ; pass pushed in, 10 mm proud
  pass.rotation.z = Math.PI / 2;
  pass.position.set(74, 24.5 + 101.5 + 1, 27.4);
  pass.userData.prop = 'pass';
  parts.table.instances[0].add(pass);

  // ---------- state handling ----------
  const cur = {};   // part -> [ {p,q,s,visible} ]
  let target = null, from = null, t0 = 0, dur = 0;
  let tableDeg = 180, cupExtended = true, stateName = 'use';

  function decompose(m) {
    const p = new THREE.Vector3(), q = new THREE.Quaternion(), s = new THREE.Vector3();
    m.decompose(p, q, s); return { p, q, s };
  }
  function stateMatrices(name) {
    const st = states[name];
    const out = {};
    for (const n of partNames) {
      const list = (st[n] || []).map(mat4);
      out[n] = list;
    }
    if (name === 'use') {
      out.table = [rzAbout(tableDeg, meta.pivot[0], meta.pivot[1])];
      if (!cupExtended) for (const k of ['ring2', 'ring3', 'ring4']) out[k] = states.book[k].map(mat4);
    }
    return out;
  }
  function snapshot() {
    const s = {};
    for (const n of partNames) s[n] = parts[n].instances.map(g => ({ p: g.position.clone(), q: g.quaternion.clone(), v: g.visible }));
    return s;
  }
  function goal(name) {
    const M = stateMatrices(name);
    const g = {};
    for (const n of partNames) {
      g[n] = parts[n].instances.map((grp, i) => {
        const m = M[n][i];
        if (!m) return { hidden: true, p: grp.position.clone(), q: grp.quaternion.clone() };
        const d = decompose(m); return { p: d.p, q: d.q, hidden: false };
      });
    }
    return g;
  }
  function applyGoal(g) {
    for (const n of partNames) parts[n].instances.forEach((grp, i) => {
      const x = g[n][i]; grp.position.copy(x.p); grp.quaternion.copy(x.q); grp.visible = !x.hidden;
    });
  }
  const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

  function setState(name, animate = true) {
    stateName = name;
    const g = goal(name);
    ctx.visible = showContext && name === 'use';
    props.visible = showProps && name === 'use' && cupExtended;
    pass.visible = showProps && name !== 'exploded';
    if (!animate) { applyGoal(g); target = null; return; }
    from = snapshot(); target = g; t0 = performance.now(); dur = animMs;
    for (const n of partNames) parts[n].instances.forEach((grp, i) => { if (!g[n][i].hidden) grp.visible = true; });
  }
  let showContext = true, showProps = true, animMs = 900;

  function step(now) {
    if (!target) return;
    const t = Math.min(1, (now - t0) / dur), e = ease(t);
    for (const n of partNames) parts[n].instances.forEach((grp, i) => {
      const a = from[n][i], b = target[n][i];
      grp.position.lerpVectors(a.p, b.p, e);
      grp.quaternion.slerpQuaternions(a.q, b.q, e);
      if (t >= 1) grp.visible = !b.hidden;
    });
    if (t >= 1) target = null;
  }

  // ---------- camera ----------
  const tmpBox = new THREE.Box3();
  function frame(view = 'hero', instant = false) {
    const V = {
      hero: { pos: [760, 560, 330], tgt: [95, 95, -70] },
      user: { pos: [720, 105, 230], tgt: [70, 105, -10] },
      wide: { pos: [1150, 900, 520], tgt: [80, 100, -250] },
      book: { pos: [430, 360, 330], tgt: [74, 105, 8] },
      exploded: { pos: [560, 520, 380], tgt: [40, 105, -30] },
      legs: { pos: [150, -420, -40], tgt: [74, 20, -45] },
      tether: { pos: [-330, -150, 260], tgt: [-5, 30, 5] },
      pass: { pos: [420, -230, 230], tgt: [200, 10, 25] },
      top: { pos: [140, 105, 900], tgt: [140, 105, 0] },
    }[view];
    const toW = v => new THREE.Vector3(v[0], v[2], -v[1]);
    const p = toW(V.pos), t = toW(V.tgt);
    if (instant) { camera.position.copy(p); controls.target.copy(t); controls.update(); return; }
    if (animMs < 50) { camera.position.copy(p); controls.target.copy(t); controls.update(); return; }
    camAnim = { p0: camera.position.clone(), p1: p, t0v: controls.target.clone(), t1: t, s: performance.now() };
  }
  let camAnim = null;
  function camStep(now) {
    if (!camAnim) return;
    const t = Math.min(1, (now - camAnim.s) / 900), e = ease(t);
    camera.position.lerpVectors(camAnim.p0, camAnim.p1, e);
    controls.target.lerpVectors(camAnim.t0v, camAnim.t1, e);
    if (t >= 1) camAnim = null;
  }

  function placeGround() {
    // ground under the suitcase (use state) or under the book
    ground.position.y = stateName === 'use' ? (showContext ? meta.z_top - 550 : meta.z_top - 0.2) : (stateName === 'exploded' ? -150 : -6.5);
    key.target.position.set(0, ground.position.y, 0);
  }

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    renderer.setSize(w, h, false);
    renderer.domElement.style.width = '100%'; renderer.domElement.style.height = '100%';
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  resize();

  // picking
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  let onPick = null, highlighted = null;
  renderer.domElement.addEventListener('pointerup', ev => {
    if (ev.pointerType === 'mouse' && ev.button !== 0) return;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hits = ray.intersectObjects(Object.values(parts).flatMap(p => p.instances), true).filter(h => h.object.visible);
    const part = hits.length ? hits[0].object.userData.part : null;
    highlight(part);
    onPick && onPick(part);
  });
  function highlight(part) {
    highlighted = part;
    for (const n of partNames) for (const g of parts[n].instances) g.traverse(o => {
      if (o.isMesh && o.userData.part) {
        if (!o.userData.baseMat) o.userData.baseMat = o.material;
        if (part && n === part) {
          const m = o.userData.baseMat.clone(); m.emissive = new THREE.Color(0xf2c200); m.emissiveIntensity = 0.25; o.material = m;
        } else o.material = o.userData.baseMat;
      }
    });
  }

  let running = true;
  function loop(now) {
    if (!running) return;
    step(now); camStep(now); placeGround(); controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  }
  setState('use', false);
  frame('hero', true);
  requestAnimationFrame(loop);

  return {
    THREE, renderer, scene, camera, controls,
    setState, frame, highlight,
    setTableAngle(d, animate = true) { tableDeg = d; if (stateName === 'use') setState('use', animate); },
    setCup(ext) { cupExtended = ext; if (stateName === 'use') setState('use', true); },
    setDuration(ms) { animMs = ms; },
    setContext(v) { showContext = v; ctx.visible = v && stateName === 'use'; },
    setProps(v) { showProps = v; props.visible = v && stateName === 'use' && cupExtended; pass.visible = v && stateName !== 'exploded'; },
    onPick(fn) { onPick = fn; },
    get state() { return stateName; },
    renderOnce() { step(performance.now() + 1e6); placeGround(); controls.update(); renderer.render(scene, camera); },
    setCameraRaw(pos, tgt) { const toW = v => new THREE.Vector3(v[0], v[2], -v[1]); camera.position.copy(toW(pos)); controls.target.copy(toW(tgt)); controls.update(); },
  };
}
