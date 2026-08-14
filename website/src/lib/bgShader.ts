const VERT = `#version 300 es
out vec2 v_uv;
void main() {
  vec2 p = vec2(
    gl_VertexID == 1 ? 3.0 : -1.0,
    gl_VertexID == 2 ? 3.0 : -1.0
  );
  v_uv = p * 0.5 + 0.5;
  gl_Position = vec4(p, 0.0, 1.0);
}
`;

const FRAG = `#version 300 es
precision highp float;

uniform sampler2D u_tex;
uniform vec2 u_res;
uniform vec2 u_texSize;
uniform float u_time;

in vec2 v_uv;
out vec4 fragColor;

float hash21(vec2 p) {
  p = fract(p * vec2(234.34, 435.345));
  p += dot(p, p + 34.23);
  return fract(p.x * p.y);
}

float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  float a = hash21(i);
  float b = hash21(i + vec2(1.0, 0.0));
  float c = hash21(i + vec2(0.0, 1.0));
  float d = hash21(i + vec2(1.0, 1.0));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p) {
  mat2 m = mat2(1.6, 1.2, -1.2, 1.6);
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; ++i) {
    v += a * vnoise(p);
    p = m * p;
    a *= 0.5;
  }
  return v;
}

float pattern(vec2 p, out vec2 q, out vec2 r) {
  q.x = fbm(p + vec2(0.0, 0.0));
  q.y = fbm(p + vec2(5.2, 1.3));
  r.x = fbm(p + 4.0 * q + vec2(1.7, 9.2));
  r.y = fbm(p + 4.0 * q + vec2(8.3, 2.8));
  return fbm(p + 4.0 * r);
}

vec3 stoneColor(vec2 p, float time) {
  vec2 q, r;

  float wave = sin(p.x * 3.0 + time * 0.35) * 0.12
             + sin(p.x * 7.0 - time * 0.25) * 0.06;
  vec2 wp = p + vec2(0.0, wave);

  float f = pattern(wp, q, r);

  float base = sin(f * 6.28318 * 9.0 + q.x * 2.0 + sin(p.x * 2.0 - time * 0.45) * 1.2);
  float fine = sin(f * 6.28318 * 22.0 + q.x * 3.0);
  float bands = 0.5 + 0.5 * mix(base, fine, 0.45);

  vec3 dark = vec3(0.10, 0.08, 0.10);
  vec3 light = vec3(0.32, 0.26, 0.28);
  vec3 crimson = vec3(0.62, 0.12, 0.16);
  vec3 aqua = vec3(0.16, 0.48, 0.46);

  vec3 col = mix(dark, light, bands);
  col = mix(col, crimson, smoothstep(0.72, 0.95, bands) * (0.5 + 0.5 * q.x) * 0.75);
  col = mix(col, aqua, smoothstep(0.02, 0.25, bands) * (0.5 + 0.5 * r.y) * 0.7);
  return col;
}

vec3 bgTint(vec3 c) {
  float lum = dot(c, vec3(0.299, 0.587, 0.114));
  c = mix(c, c * c * (3.0 - 2.0 * c), 0.45);
  vec3 shadow = vec3(0.12, 0.06, 0.10);
  vec3 mid = vec3(0.32, 0.16, 0.20);
  vec3 hi = vec3(0.16, 0.40, 0.40);
  vec3 grade = mix(shadow, mid, smoothstep(0.0, 0.5, lum));
  grade = mix(grade, hi, smoothstep(0.5, 1.0, lum));
  return mix(c, grade, 0.28);
}

void main() {
  vec2 uv = v_uv;
  float t = u_time * 0.15;

  vec2 d = vec2(
    fbm(uv * 2.0 + vec2(t, t * 0.7)),
    fbm(uv * 2.0 + vec2(t * 0.7, t) + 3.7)
  );

  vec2 uvd = uv + (d - 0.5) * 0.03;

  float scale = max(u_res.x / u_texSize.x, u_res.y / u_texSize.y);
  vec2 scaled = u_texSize * scale;
  vec2 off = (u_res - scaled) * 0.5;
  vec2 texUv = clamp((uvd * u_res - off) / scaled, 0.0, 1.0);

  vec3 col = bgTint(texture(u_tex, texUv).rgb);

  vec2 drift = vec2(u_time * 0.006, u_time * 0.004);
  vec2 TR = uv - vec2(1.0, 0.0);
  vec2 BL = uv - vec2(0.0, 1.0);

  vec3 stoneTR = stoneColor(TR * 1.7 + drift, u_time);
  vec3 stoneBL = stoneColor(BL * 1.7 + drift, u_time);

  float mTR = smoothstep(0.9, 0.45, length(TR));
  float mBL = smoothstep(0.9, 0.45, length(BL));

  col = mix(col, stoneTR, mTR * 0.28);
  col = mix(col, stoneBL, mBL * 0.28);

  float glTR = exp(-length(TR) * 4.0);
  float glBL = exp(-length(BL) * 4.0);
  col += vec3(0.22, 0.07, 0.10) * glTR * 0.10;
  col += vec3(0.06, 0.20, 0.20) * glBL * 0.08;

  float dist = length(uv - 0.5);
  col *= 1.0 - 0.45 * smoothstep(0.5, 1.2, dist);

  float grain = hash21(uv * u_res + vec2(t * 137.0, t * 173.0));
  grain = (grain - 0.5) * (0.25 + 0.75 * dot(col, vec3(0.299, 0.587, 0.114)));
  col += grain * 0.02;

  fragColor = vec4(col, 1.0);
}
`;

const MAX_TEXTURE = 1920;
const MAX_DPR = 1.5;

export class BackgroundShader {
  private canvas: HTMLCanvasElement;
  private gl: WebGL2RenderingContext | null = null;
  private program: WebGLProgram | null = null;
  private texture: WebGLTexture | null = null;
  private uTime: WebGLUniformLocation | null = null;
  private uRes: WebGLUniformLocation | null = null;
  private uTexSize: WebGLUniformLocation | null = null;
  private texWidth = 1;
  private texHeight = 1;
  private rafId = 0;
  private lastFrame = 0;
  private startTime = 0;
  private running = false;
  private disposed = false;
  private texReady = false;
  private observer: ResizeObserver | null = null;

  constructor(canvas: HTMLCanvasElement, imageUrl: string) {
    this.canvas = canvas;
    if (!this.initGl()) return;
    this.prepareTexture(imageUrl);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(canvas);
    this.resize();
  }

  private initGl(): boolean {
    const gl = this.canvas.getContext("webgl2", {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      premultipliedAlpha: true,
      powerPreference: "high-performance",
    });
    if (!gl) return false;
    this.gl = gl;

    const vs = this.compile(gl.VERTEX_SHADER, VERT);
    const fs = this.compile(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return false;

    const prog = gl.createProgram();
    if (!prog) return false;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.error("[bgShader] program link failed:", gl.getProgramInfoLog(prog));
      return false;
    }
    this.program = prog;
    gl.useProgram(prog);

    this.uTime = gl.getUniformLocation(prog, "u_time");
    this.uRes = gl.getUniformLocation(prog, "u_res");
    this.uTexSize = gl.getUniformLocation(prog, "u_texSize");
    if (this.uTexSize) gl.uniform2f(this.uTexSize, 1, 1);

    const tex = gl.createTexture();
    if (!tex) return false;
    this.texture = tex;
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texImage2D(
      gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE,
      new Uint8Array([13, 13, 13, 255]),
    );
    const loc = gl.getUniformLocation(prog, "u_tex");
    if (loc) gl.uniform1i(loc, 0);
    return true;
  }

  private compile(type: number, source: string): WebGLShader | null {
    const gl = this.gl;
    if (!gl) return null;
    const sh = gl.createShader(type);
    if (!sh) return null;
    gl.shaderSource(sh, source);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      console.error("[bgShader] shader compile failed:", gl.getShaderInfoLog(sh));
      gl.deleteShader(sh);
      return null;
    }
    return sh;
  }

  private prepareTexture(imageUrl: string): void {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => this.upload(img);
    img.src = imageUrl;
  }

  private upload(img: HTMLImageElement): void {
    const gl = this.gl;
    if (!gl || !this.texture || this.disposed) return;
    const scale = Math.min(1, MAX_TEXTURE / Math.max(img.naturalWidth, img.naturalHeight));
    const w = Math.max(1, Math.round(img.naturalWidth * scale));
    const h = Math.max(1, Math.round(img.naturalHeight * scale));
    const off = document.createElement("canvas");
    off.width = w;
    off.height = h;
    const octx = off.getContext("2d");
    if (!octx) return;
    octx.drawImage(img, 0, 0, w, h);
    this.texWidth = w;
    this.texHeight = h;
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.texture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, off);
    if (this.uTexSize) gl.uniform2f(this.uTexSize, w, h);
    this.texReady = true;
  }

  private resize(): void {
    const gl = this.gl;
    if (!gl) return;
    const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
    const w = Math.max(1, Math.round(this.canvas.clientWidth * dpr));
    const h = Math.max(1, Math.round(this.canvas.clientHeight * dpr));
    if (this.canvas.width !== w || this.canvas.height !== h) {
      this.canvas.width = w;
      this.canvas.height = h;
    }
    gl.viewport(0, 0, w, h);
    if (this.uRes) gl.uniform2f(this.uRes, w, h);
  }

  start(): void {
    if (this.running || !this.gl || !this.program) return;
    this.running = true;
    this.startTime = performance.now();
    this.rafId = requestAnimationFrame(this.frame);
  }

  private frame = (now: number): void => {
    if (!this.running || this.disposed) return;
    if (!document.hidden && this.texReady && now - this.lastFrame >= 33) {
      this.lastFrame = now;
      this.resize();
      const gl = this.gl;
      if (gl && this.program) {
        if (this.uTime) gl.uniform1f(this.uTime, (now - this.startTime) / 1000);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      }
    }
    this.rafId = requestAnimationFrame(this.frame);
  };

  stop(): void {
    this.running = false;
    cancelAnimationFrame(this.rafId);
  }

  dispose(): void {
    this.disposed = true;
    this.stop();
    this.observer?.disconnect();
    const gl = this.gl;
    if (gl) {
      if (this.texture) gl.deleteTexture(this.texture);
      if (this.program) gl.deleteProgram(this.program);
    }
  }
}