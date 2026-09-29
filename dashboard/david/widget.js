// AI David loader: the only script a page needs.
//   Homepage: <div data-ai-david-inline></div> + <script src="/david/widget.js" defer>
//     -> AI David is embedded in that element; code and face frames load when it scrolls near the screen.
//   Other pages (ESC, injected by nginx): <script src="/david/widget.js" data-context="esc" defer>
//     -> a floating "Ask AI David" bubble; everything loads on first open.
(function () {
  "use strict";
  const V = "6";
  const script = document.currentScript;
  const context = (script && script.dataset.context) || "home";

  function load(src, tag) {
    return new Promise((ok, fail) => {
      const n = document.createElement(tag);
      if (tag === "link") { n.rel = "stylesheet"; n.href = src; } else { n.src = src; }
      n.onload = ok;
      n.onerror = fail;
      document.head.appendChild(n);
    });
  }
  let assets = null;
  const loadAssets = () => assets || (assets = Promise.all([
    load("/david/david.css?v=" + V, "link"),
    load("/david/david.js?v=" + V, "script"),
  ]));

  // --- embedded ---
  const spot = document.querySelector("[data-ai-david-inline]");
  if (spot) {
    const mountInline = () => loadAssets()
      .then(() => window.AIDavid.mount(spot, { size: "inline", context }))
      .catch(() => { spot.textContent = "AI David couldn't load. Try again in a minute."; });
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) { io.disconnect(); mountInline(); }
      }, { rootMargin: "300px" });
      io.observe(spot);
    } else {
      mountInline();
    }
    return;
  }

  // --- floating bubble ---
  // On ESC the bubble sits top-right, just under Streamlit's header bar; elsewhere bottom-right.
  const atTop = context === "esc";
  const edge = atTop ? "top: 64px" : "bottom: 20px";
  const css = `
  .aidw-bubble { position: fixed; right: 20px; ${edge}; z-index: 1000000; display: flex;
    align-items: center; gap: 10px; padding: 6px 16px 6px 6px; border: 1px solid rgba(148,163,184,.25);
    border-radius: 999px; background: rgba(15,23,42,.92); color: #f1f5f9; font: 600 14px "Inter", system-ui, sans-serif;
    cursor: pointer; box-shadow: 0 8px 28px rgba(0,0,0,.45); backdrop-filter: blur(6px); }
  .aidw-bubble img { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; object-position: 50% 30%; }
  .aidw-bubble:hover { border-color: #6366f1; }
  .aidw-panel { position: fixed; right: 20px; ${edge}; z-index: 1000001; width: 360px;
    height: min(640px, calc(100vh - ${atTop ? 84 : 40}px)); display: none; flex-direction: column; padding: 14px;
    border: 1px solid rgba(148,163,184,.25); border-radius: 18px; background: #0f172a;
    box-shadow: 0 16px 48px rgba(0,0,0,.6); box-sizing: border-box; }
  .aidw-open .aidw-panel { display: flex; }
  .aidw-open .aidw-bubble { display: none; }
  .aidw-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
    font: 600 14px "Inter", system-ui, sans-serif; color: #f1f5f9; }
  .aidw-close { background: none; border: 0; color: #94a3b8; font-size: 22px; line-height: 1; cursor: pointer; }
  .aidw-body { flex: 1; min-height: 0; }
  @media (max-width: 520px) {
    .aidw-bubble { right: 12px; }
    .aidw-panel { inset: 0; width: auto; height: 100%; border-radius: 0; }
  }`;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  const wrap = document.createElement("div");
  wrap.className = "aidw";
  wrap.innerHTML = `
    <button class="aidw-bubble" type="button" aria-label="Open AI David chat">
      <img src="/david/frames/rest.webp" alt=""> Ask AI David
    </button>
    <div class="aidw-panel" role="dialog" aria-label="AI David">
      <div class="aidw-top"><span>AI David</span>
        <button class="aidw-close" type="button" aria-label="Close">×</button>
      </div>
      <div class="aidw-body"></div>
    </div>`;
  document.body.appendChild(wrap);

  let chat = null;
  wrap.querySelector(".aidw-bubble").addEventListener("click", async () => {
    wrap.classList.add("aidw-open");
    if (chat) return;
    chat = "loading";
    try {
      await loadAssets();
      chat = window.AIDavid.mount(wrap.querySelector(".aidw-body"), { size: "widget", context });
      wrap.querySelector(".aid-input").focus();
    } catch (e) {
      chat = null;
      wrap.querySelector(".aidw-body").textContent = "AI David couldn't load. Try again in a minute.";
    }
  });
  wrap.querySelector(".aidw-close").addEventListener("click", () => {
    wrap.classList.remove("aidw-open");
    if (chat && chat.stop) chat.stop();
  });
})();
