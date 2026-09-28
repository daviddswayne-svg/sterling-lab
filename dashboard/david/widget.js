// Homepage "Ask David" bubble. Loads only a small avatar until clicked; the face frames,
// styles and chat code (david.js) load on first open so the homepage stays light.
(function () {
  "use strict";
  const css = `
  .aidw-bubble { position: fixed; right: 20px; bottom: 20px; z-index: 900; display: flex; align-items: center;
    gap: 10px; padding: 6px 16px 6px 6px; border: 1px solid rgba(148,163,184,.25); border-radius: 999px;
    background: rgba(15,23,42,.92); color: #f1f5f9; font: 600 14px "Inter", system-ui, sans-serif; cursor: pointer;
    box-shadow: 0 8px 28px rgba(0,0,0,.45); backdrop-filter: blur(6px); }
  .aidw-bubble img { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; object-position: 50% 30%; }
  .aidw-bubble:hover { border-color: #6366f1; }
  .aidw-panel { position: fixed; right: 20px; bottom: 20px; z-index: 901; width: 360px;
    height: min(640px, calc(100vh - 40px)); display: none; flex-direction: column; padding: 14px;
    border: 1px solid rgba(148,163,184,.25); border-radius: 18px; background: #0f172a;
    box-shadow: 0 16px 48px rgba(0,0,0,.6); box-sizing: border-box; }
  .aidw-open .aidw-panel { display: flex; }
  .aidw-open .aidw-bubble { display: none; }
  .aidw-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
    font: 600 14px "Inter", system-ui, sans-serif; color: #f1f5f9; }
  .aidw-close { background: none; border: 0; color: #94a3b8; font-size: 22px; line-height: 1; cursor: pointer; }
  .aidw-body { flex: 1; min-height: 0; }
  @media (max-width: 520px) {
    .aidw-bubble { right: 12px; bottom: 12px; }
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
  function load(src, tag) {
    return new Promise((ok, fail) => {
      const n = document.createElement(tag);
      if (tag === "link") { n.rel = "stylesheet"; n.href = src; } else { n.src = src; }
      n.onload = ok;
      n.onerror = fail;
      document.head.appendChild(n);
    });
  }

  async function open() {
    wrap.classList.add("aidw-open");
    if (chat) return;
    chat = "loading";
    try {
      await Promise.all([load("/david/david.css?v=2", "link"), load("/david/david.js?v=2", "script")]);
      chat = window.AIDavid.mount(wrap.querySelector(".aidw-body"), { size: "widget" });
      wrap.querySelector(".aid-input").focus();
    } catch (e) {
      chat = null;
      wrap.querySelector(".aidw-body").textContent = "AI David couldn't load. Try again in a minute.";
    }
  }
  wrap.querySelector(".aidw-bubble").addEventListener("click", open);
  // Anything on the page marked data-open-ai-david (the homepage CTA) opens the widget too.
  document.querySelectorAll("[data-open-ai-david]").forEach((a) => a.addEventListener("click", (ev) => {
    ev.preventDefault();
    open();
  }));
  wrap.querySelector(".aidw-close").addEventListener("click", () => {
    wrap.classList.remove("aidw-open");
    if (chat && chat.stop) chat.stop();
  });
})();
