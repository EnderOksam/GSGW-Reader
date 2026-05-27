<script lang="ts">
  import { onDestroy, onMount } from "svelte";

  let canvas: HTMLCanvasElement;
  let frame = 0;
  let gl: WebGLRenderingContext | null = null;
  let program: WebGLProgram | null = null;
  let startedAt = 0;
  let timeUniform: WebGLUniformLocation | null = null;
  let resolutionUniform: WebGLUniformLocation | null = null;
  let seedUniform: WebGLUniformLocation | null = null;
  let isRunning = false;

  const COLORS = [
    "#1C3760",
    "#4682B4",
    "#FF69B4",
    "#FF4500",
    "#4B0082",
    "#C0C0C0",
    "#FFFF00",
    "#3A2E3B",
    "#E0115F",
  ];

  const hexToRgb = (hex: string): [number, number, number] => {
    const h = hex.replace("#", "").padEnd(6, "0").slice(0, 6);
    return [
      parseInt(h.slice(0, 2), 16) / 255,
      parseInt(h.slice(2, 4), 16) / 255,
      parseInt(h.slice(4, 6), 16) / 255,
    ];
  };

  const vertexSrc = `
    attribute vec2 a_position;
    varying vec2 v_uv;
    void main() {
      v_uv = a_position * 0.5 + 0.5;
      gl_Position = vec4(a_position, 0.0, 1.0);
    }
  `;

  const fragmentSrc = `
    precision highp float;

    varying vec2 v_uv;
    uniform vec2 u_resolution;
    uniform float u_time;
    uniform float u_seed;
    uniform vec3 u_c0, u_c1, u_c2, u_c3, u_c4, u_c5, u_c6, u_c7, u_c8;

    float hash(vec2 p) {
      p += vec2(u_seed, u_seed * 1.37);
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
    }

    float noise(vec2 p) {
      vec2 i = floor(p);
      vec2 f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      float a = hash(i);
      float b = hash(i + vec2(1.0, 0.0));
      float c = hash(i + vec2(0.0, 1.0));
      float d = hash(i + vec2(1.0, 1.0));
      return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
    }

    float fbm(vec2 p) {
      float value = 0.0;
      float amp = 0.5;
      for (int i = 0; i < 3; i++) {
        value += amp * noise(p);
        p *= mat2(1.72, 0.42, -0.38, 1.64);
        amp *= 0.5;
      }
      return value;
    }

    float band(float v, float w) {
      return 1.0 - smoothstep(0.0, w, abs(v));
    }

    mat2 rot(float a) {
      float s = sin(a), c = cos(a);
      return mat2(c, -s, s, c);
    }

    void main() {
      vec2 uv = v_uv;
      vec2 asp = vec2(u_resolution.x / u_resolution.y, 1.0);
      vec2 p = (uv - 0.5) * asp;

      float t = u_time * 0.035;
      float fA = fbm(p * 1.22 + vec2(t * 0.12, -t * 0.08));
      vec2 trn = rot(0.85 + fA * 0.45) * p;
      float fB = fbm(trn * 2.35 + vec2(-t * 0.09, t * 0.11) + fA * 0.55);
      float fC = fbm(rot(-1.15) * p * 1.75 + vec2(fB * 0.5 - t * 0.04, fA * 0.45 + t * 0.06));

      float ang = (fA * 2.2 + fB * 1.1 + t * 0.18) * 6.2831853;
      vec2 curl = vec2(sin(p.y * 7.0 + fB * 5.2 - t * 0.24), cos(p.x * 6.4 - fA * 5.6 + t * 0.18));
      vec2 w = p + vec2(cos(ang), sin(ang)) * 0.12 + vec2(fB - 0.5, 0.5 - fA) * 0.13 + curl * 0.075;

      float wave = sin((w.x * 3.15 + w.y * 1.35 + fA * 2.65 + fC * 1.2 + t * 0.52) * 3.1415926)
                 + sin((w.x * -1.25 + w.y * 3.8 + fB * 2.15 - t * 0.38) * 3.1415926) * 0.46;
      float cross = sin((w.x * 3.95 - w.y * 2.65 + fC * 2.55 + t * 0.22) * 3.1415926);
      float back = sin((w.x * -2.6 - w.y * 3.15 + fA * 1.75 - fB * 1.4 - t * 0.16) * 3.1415926);
      wave += cross * 0.28 + back * 0.2;

      float cA = sin(atan(w.y + 0.32, w.x - 0.05) * 2.8 + length(w - vec2(-0.32, 0.05)) * 13.5 + fA * 4.2 - t * 0.22);
      float cB = sin(atan(w.y + 0.18, w.x - 0.28) * -2.4 + length(w - vec2(0.28, -0.18)) * 12.0 + fC * 4.0 + t * 0.16);
      float vInk = sin((w.x * 1.35 + w.y * 6.5 + fB * 3.6 - t * 0.22) * 3.1415926);

      float sheet = smoothstep(-0.62, 0.44, wave + fB * 0.46 + 0.02);
      float vein = max(band(wave + fA * 0.12, 0.18), max(band(cross + fC * 0.18, 0.1), band(back - fB * 0.12, 0.09)) * 0.72);
      float sharp = max(band(wave - fB * 0.18, 0.052), max(band(cross - fA * 0.16, 0.04), band(back + fC * 0.12, 0.038)) * 0.76);
      vein = max(vein, max(band(cA, 0.16), band(cB, 0.14)) * 0.94);
      sharp = max(sharp, max(max(band(cA, 0.055), band(cB, 0.05)), band(vInk, 0.055)) * 0.9);
      float shadow = smoothstep(0.14, -0.18, uv.x + uv.y * 0.68 - 0.34);
      float grain = hash(gl_FragCoord.xy) - 0.5;
      float vig = smoothstep(0.78, 0.18, length(uv - vec2(0.5, 0.52)));

      vec3 base = mix(mix(u_c2, u_c7, 0.34), vec3(0.0), 0.86);
      vec3 rA = mix(mix(u_c0, u_c8, 0.24), vec3(0.92, 0.01, 0.0), 0.58);
      vec3 rB = mix(mix(u_c8, u_c5, 0.16), vec3(0.78, 0.0, 0.0), 0.56);
      vec3 rC = mix(mix(u_c1, u_c3, 0.22), vec3(0.58, 0.0, 0.02), 0.46);
      vec3 ink = mix(mix(u_c2, u_c7, 0.2), vec3(0.0), 0.96);
      vec3 edge = mix(mix(u_c4, u_c6, 0.24), vec3(0.015, 0.0, 0.0), 0.74);

      vec3 color = mix(base, mix(rA, rB, fB), sheet);
      color = mix(color, rC, max(0.0, sheet - 0.54) * 0.52);
      color = mix(color, edge, vein * 0.68);
      color = mix(color, ink, sharp * 0.96);
      color = mix(color, ink, shadow * 0.64);
      color = mix(color, base, (1.0 - vig) * 0.36);
      color += grain * 0.03;
      color = mix(vec3(dot(color, vec3(0.299, 0.587, 0.114))), color, 1.28);
      color = clamp((color - 0.5) * 1.08 + 0.5, 0.0, 1.0);

      gl_FragColor = vec4(color, 1.0);
    }
  `;

  const uniformNames = ["u_c0", "u_c1", "u_c2", "u_c3", "u_c4", "u_c5", "u_c6", "u_c7", "u_c8"];
  const colorUniforms: (WebGLUniformLocation | null)[] = [];

  function compile(type: number, src: string) {
    if (!gl) return null;
    const s = gl.createShader(type);
    if (!s) return null;
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      gl.deleteShader(s);
      return null;
    }
    return s;
  }

  function link() {
    if (!gl) return null;
    const vs = compile(gl.VERTEX_SHADER, vertexSrc);
    const fs = compile(gl.FRAGMENT_SHADER, fragmentSrc);
    if (!vs || !fs) return null;
    const prog = gl.createProgram();
    if (!prog) return null;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      gl.deleteProgram(prog);
      return null;
    }
    return prog;
  }

  function resize() {
    if (!gl) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 0.82);
    const maxPx = 420_000;
    const rw = Math.max(1, Math.round(window.innerWidth * dpr));
    const rh = Math.max(1, Math.round(window.innerHeight * dpr));
    const s = Math.min(1, Math.sqrt(maxPx / (rw * rh)));
    const w = Math.max(1, Math.round(rw * s));
    const h = Math.max(1, Math.round(rh * s));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    gl.viewport(0, 0, w, h);
  }

  function uploadColors() {
    if (!gl || !program) return;
    for (let i = 0; i < COLORS.length; i++) {
      const loc = gl.getUniformLocation(program, uniformNames[i]);
      if (!loc) continue;
      const rgb = hexToRgb(COLORS[i]);
      gl.uniform3f(loc, rgb[0], rgb[1], rgb[2]);
    }
  }

  function frameLoop(now: number) {
    if (!gl || !program) return;
    frame = requestAnimationFrame(frameLoop);
    gl.uniform1f(timeUniform, (now - startedAt) * 0.001);
    gl.uniform2f(resolutionUniform, canvas.width, canvas.height);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }

  function handleVis() {
    if (document.hidden) {
      if (isRunning) { isRunning = false; cancelAnimationFrame(frame); }
    } else {
      if (!isRunning) { isRunning = true; startedAt = performance.now(); frame = requestAnimationFrame(frameLoop); }
    }
  }

  onMount(() => {
    gl = canvas.getContext("webgl", { alpha: false, antialias: false, depth: false, stencil: false, powerPreference: "high-performance", preserveDrawingBuffer: false });
    if (!gl) return;

    program = link();
    if (!program) return;

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1]), gl.STATIC_DRAW);
    gl.useProgram(program);

    timeUniform = gl.getUniformLocation(program, "u_time");
    resolutionUniform = gl.getUniformLocation(program, "u_resolution");
    seedUniform = gl.getUniformLocation(program, "u_seed");
    gl.uniform1f(seedUniform, Math.random() * 1000);

    uploadColors();

    const pos = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);

    resize();
    startedAt = performance.now();
    isRunning = true;
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", handleVis);
    frame = requestAnimationFrame(frameLoop);
  });

  onDestroy(() => {
    if (typeof cancelAnimationFrame !== "undefined") cancelAnimationFrame(frame);
    if (typeof window !== "undefined") window.removeEventListener("resize", resize);
    if (typeof document !== "undefined") document.removeEventListener("visibilitychange", handleVis);
    if (gl && program) gl.deleteProgram(program);
  });
</script>

<canvas bind:this={canvas} class="ink-texture" aria-hidden="true"></canvas>

<style>
  .ink-texture {
    position: fixed;
    inset: 0;
    z-index: -10;
    width: 100%;
    height: 100%;
    pointer-events: none;
    background: #050303;
    filter: blur(11px);
    transform: scale(1.008);
  }
</style>
