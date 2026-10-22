import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";
import ts from "typescript";

function loadModule(name, globals) {
  const source = readFileSync(new URL(`../src/lib/reader/${name}.ts`, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  });
  const context = { exports: {}, ...globals };
  vm.runInNewContext(outputText, context);
  return context.exports;
}

function scareHarness() {
  let now = 0;
  let nextTimer = 0;
  let onIntersection;
  const timers = new Map();
  const frames = [];
  const listeners = new Map();
  const windows = [];
  const window = {
    scrollY: 0,
    innerHeight: 800,
    addEventListener(name, fn) { listeners.set(name, fn); },
    removeEventListener(name) { listeners.delete(name); },
    scrollTo(options) { this.scrollY = options.top; },
  };
  const { initScareScroll } = loadModule("scare-scroll", {
    window,
    document: {
      body: {},
      documentElement: { scrollHeight: 10000 },
      querySelectorAll: () => windows,
    },
    performance: { now: () => now },
    requestAnimationFrame: fn => frames.push(fn),
    setTimeout(fn, delay) {
      const id = ++nextTimer;
      timers.set(id, { fn, due: now + delay });
      return id;
    },
    clearTimeout: id => timers.delete(id),
    IntersectionObserver: class {
      constructor(callback) { onIntersection = callback; }
      observe() {}
      disconnect() {}
    },
    MutationObserver: class {
      observe() {}
      disconnect() {}
    },
  });
  const cleanup = initScareScroll(window);
  return {
    cleanup,
    addScare() {
      const classes = new Set();
      const win = {
        getBoundingClientRect: () => ({ top: 300, height: 200 }),
        closest: () => zone,
      };
      const zone = {
        classList: { add: value => classes.add(value) },
        querySelector: () => win,
      };
      windows.push(win);
      return { classes, win, zone };
    },
    enter(...scares) {
      onIntersection(scares.map(scare => ({ target: scare.win, isIntersecting: true })));
    },
    dispatch(name) { listeners.get(name)?.(); },
    flushFrames() {
      for (const fn of frames.splice(0)) fn(now);
    },
    advance(ms) {
      now += ms;
      for (const [id, timer] of [...timers]) {
        if (timer.due <= now) {
          timers.delete(id);
          timer.fn();
        }
      }
    },
    isScrollLocked() {
      let blocked = false;
      listeners.get("wheel")?.({
        preventDefault() { blocked = true; },
        stopPropagation() {},
      });
      return blocked;
    },
  };
}

for (const input of ["click", "touchstart"]) {
  test(`early ${input} releases scrolling and still reveals the scare`, () => {
    const h = scareHarness();
    const scare = h.addScare();
    h.enter(scare);
    assert.equal(h.isScrollLocked(), true);
    h.dispatch(input);
    h.flushFrames();
    assert.equal(h.isScrollLocked(), false, "a stale arrival must not re-lock scrolling");
    h.advance(179);
    assert.equal(scare.classes.has("scare-active"), false);
    h.advance(1);
    assert.equal(scare.classes.has("scare-active"), true);
  });
}

test("normal arrival reveals once and releases its scroll lock", () => {
  const h = scareHarness();
  const scare = h.addScare();
  h.enter(scare);
  h.flushFrames();
  h.advance(180);
  assert.equal(scare.classes.has("scare-active"), true);
  assert.equal(h.isScrollLocked(), true);
  h.advance(620);
  assert.equal(h.isScrollLocked(), false);
  h.enter(scare);
  assert.equal(h.isScrollLocked(), false, "revisiting a revealed scare must not lock again");
});

test("overlapping scares both reveal and the newest lock gets its full duration", () => {
  const h = scareHarness();
  const first = h.addScare();
  const second = h.addScare();
  h.enter(first);
  h.flushFrames();
  h.advance(100);
  h.enter(second);
  h.flushFrames();
  h.advance(180);
  assert.equal(first.classes.has("scare-active"), true);
  assert.equal(second.classes.has("scare-active"), true);
  h.advance(520);
  assert.equal(h.isScrollLocked(), true, "the first scare's old timer must not unlock the second");
  h.advance(100);
  assert.equal(h.isScrollLocked(), false);
});

test("leaving the chapter cancels every pending reveal", () => {
  const h = scareHarness();
  const scares = [h.addScare(), h.addScare()];
  h.enter(...scares);
  h.cleanup();
  h.flushFrames();
  h.advance(1000);
  assert.equal(h.isScrollLocked(), false);
  for (const scare of scares) assert.equal(scare.classes.has("scare-active"), false);
});

test("a temporarily missing window does not permanently consume a scare", () => {
  const h = scareHarness();
  const scare = h.addScare();
  scare.zone.querySelector = () => null;
  h.enter(scare);
  scare.zone.querySelector = () => scare.win;
  h.enter(scare);
  h.advance(180);
  assert.equal(scare.classes.has("scare-active"), true);
});

test("scare effects share wrapper visibility while ordinary effects remain independent", () => {
  const observers = [];
  const element = wrapper => ({
    attributes: new Set(["data-anim-off"]),
    closest: () => wrapper,
    setAttribute(name) { this.attributes.add(name); },
    removeAttribute(name) { this.attributes.delete(name); },
  });
  const wrapper = element();
  wrapper.closest = () => wrapper;
  const first = element(wrapper);
  const second = element(wrapper);
  const ordinary = element(null);
  const article = { querySelectorAll: () => [ordinary, wrapper, first, second] };
  const { observeAnimationVisibility } = loadModule("randomize-animations", {
    document: { querySelectorAll: () => [article] },
    IntersectionObserver: class {
      targets = [];
      disconnected = false;
      constructor(callback) { this.callback = callback; observers.push(this); }
      observe(target) { this.targets.push(target); }
      disconnect() { this.disconnected = true; }
    },
  });
  observeAnimationVisibility();
  const observer = observers[0];
  assert.deepEqual(observer.targets, [ordinary, wrapper]);
  for (const effect of [first, second]) {
    assert.equal(effect.attributes.has("data-anim-off"), false, "stale per-effect pause flags must be cleared");
  }
  observer.callback([{ target: wrapper, isIntersecting: true }]);
  assert.equal(wrapper.attributes.has("data-anim-off"), false);
  assert.equal(ordinary.attributes.has("data-anim-off"), true);
  observer.callback([{ target: wrapper, isIntersecting: false }]);
  assert.equal(wrapper.attributes.has("data-anim-off"), true);
  observer.callback([{ target: wrapper, isIntersecting: true }]);
  assert.equal(wrapper.attributes.has("data-anim-off"), false);
  observeAnimationVisibility();
  assert.equal(observer.disconnected, true);
  assert.deepEqual(observers[1].targets, [ordinary, wrapper]);
});
