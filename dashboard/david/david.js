// AI David: David's photo, lip-synced to his cloned voice, with a chat box.
// Shared by the homepage widget (widget.js) and the /david/ page.
//   AIDavid.mount(element, { size: "widget" | "page" })
// Frames are LivePortrait renders of one photo (~/Projects/ai-david/gen_frames.py on the M3).
// The API (/api/david/chat) returns the reply, the MP3 and per-character timings from ElevenLabs;
// on every animation frame we look up the character being spoken and show its mouth shape.
(function () {
  "use strict";
  const BASE = "/david/frames/";
  const FRAMES = ["rest", "mbp", "slight", "aa", "ee", "oh", "oo", "blink1", "blink2", "smile"];
  const MAX_HISTORY = 6;

  // Letter -> mouth shape. Vowels drive most of the look; spaces and punctuation close the mouth.
  function visemeFor(ch) {
    const c = (ch || "").toLowerCase();
    if (c === "a") return "aa";
    if (c === "e" || c === "i" || c === "y") return "ee";
    if (c === "o") return "oh";
    if (c === "u" || c === "w" || c === "q") return "oo";
    if (c === "m" || c === "b" || c === "p") return "mbp";
    if (/[a-z0-9]/.test(c)) return "slight";
    return "rest";
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function mount(root, opts) {
    opts = opts || {};
    root.classList.add("aid", "aid-" + (opts.size || "page"));

    // --- face ---
    const face = el("div", "aid-face");
    const head = el("div", "aid-head");
    const imgs = {};
    FRAMES.forEach((name) => {
      const img = el("img", "aid-frame");
      img.src = BASE + name + ".webp";
      img.alt = name === "rest" ? "AI David" : "";
      img.draggable = false;
      if (name === "rest") img.classList.add("on");
      imgs[name] = img;
      head.appendChild(img);
    });
    face.appendChild(head);

    const label = el("p", "aid-label");
    label.append(el("strong", null, "AI David"),
      " · an AI version of David Swayne, in his cloned voice. It can make mistakes.");

    // --- chat ---
    const log = el("div", "aid-log");
    log.setAttribute("aria-live", "polite");
    const form = el("form", "aid-form");
    const input = el("input", "aid-input");
    input.type = "text";
    input.maxLength = 500;
    input.placeholder = "Ask me anything…";
    input.setAttribute("aria-label", "Ask AI David a question");
    const send = el("button", "aid-send", "Ask");
    send.type = "submit";
    form.append(input, send);

    const meta = el("div", "aid-meta");
    const left = el("span", "aid-left", "20 questions a day");
    const mute = el("button", "aid-mute", "🔊 Sound on");
    mute.type = "button";
    meta.append(left, mute);

    root.append(face, label, log, form, meta);
    say("assistant", "Hi, I'm AI David. Ask me about my work, the projects on this site, or anything really.");

    // --- state ---
    let shown = "rest";
    let speaking = false;
    let muted = false;
    let audioCtx = null;
    let gain = null;
    let source = null;
    const history = [];

    function show(name) {
      if (name === shown) return;
      imgs[shown].classList.remove("on");
      imgs[name].classList.add("on");
      shown = name;
    }

    function say(role, text, note) {
      const msg = el("div", "aid-msg aid-" + role);
      msg.append(el("span", "aid-text", text));
      if (note) msg.append(el("span", "aid-note", note));
      log.append(msg);
      log.scrollTop = log.scrollHeight;
      return msg;
    }

    // Idle life: a blink every few seconds, only while the mouth is at rest.
    (function blinkLoop() {
      setTimeout(() => {
        if (!speaking && shown === "rest") {
          show("blink1");
          setTimeout(() => show("blink2"), 50);
          setTimeout(() => show("blink1"), 130);
          setTimeout(() => { if (!speaking) show("rest"); }, 180);
        }
        blinkLoop();
      }, 2500 + Math.random() * 3500);
    })();

    mute.addEventListener("click", () => {
      muted = !muted;
      mute.textContent = muted ? "🔇 Sound off" : "🔊 Sound on";
      if (gain) gain.gain.value = muted ? 0 : 1;
    });

    function ensureAudio() {
      // Must be created inside the click/submit handler or browsers keep it suspended.
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        gain = audioCtx.createGain();
        gain.gain.value = muted ? 0 : 1;
        gain.connect(audioCtx.destination);
      }
      if (audioCtx.state === "suspended") audioCtx.resume();
    }

    function stopSpeaking() {
      if (source) { try { source.stop(); } catch (e) { /* already stopped */ } }
      source = null;
      speaking = false;
      root.classList.remove("aid-talking");
      show("rest");
    }

    async function speak(b64, alignment) {
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const buffer = await audioCtx.decodeAudioData(bytes.buffer);
      stopSpeaking();
      source = audioCtx.createBufferSource();
      source.buffer = buffer;
      source.connect(gain);
      const chars = alignment.characters || [];
      const starts = alignment.character_start_times_seconds || [];
      const ends = alignment.character_end_times_seconds || [];
      const t0 = audioCtx.currentTime + 0.05;
      let i = 0;
      let current = "rest";
      let since = 0;
      speaking = true;
      root.classList.add("aid-talking");
      source.onended = () => {
        stopSpeaking();
        show("smile");
        setTimeout(() => { if (!speaking && shown === "smile") show("rest"); }, 1200);
      };
      source.start(t0);
      (function tick() {
        if (!speaking) return;
        const t = audioCtx.currentTime - t0;
        while (i < chars.length - 1 && ends[i] <= t) i++;
        const want = t >= starts[i] && t < ends[i] ? visemeFor(chars[i]) : "rest";
        // Hold each shape ~60 ms so fast letters don't flicker.
        if (want !== current && t - since > 0.06) {
          current = want;
          since = t;
          show(want);
        }
        requestAnimationFrame(tick);
      })();
    }

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const text = input.value.trim();
      if (!text || send.disabled) return;
      ensureAudio();
      stopSpeaking();
      input.value = "";
      say("user", text);
      const thinking = say("assistant", "…");
      thinking.classList.add("aid-thinking");
      send.disabled = true;
      root.classList.add("aid-busy");
      try {
        const r = await fetch("/api/david/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, history: history.slice(-MAX_HISTORY) }),
        });
        const data = await r.json().catch(() => ({}));
        thinking.remove();
        if (typeof data.remaining === "number") {
          left.textContent = data.remaining + " question" + (data.remaining === 1 ? "" : "s") + " left today";
        }
        if (!r.ok) {
          say("assistant", data.error || "Something went wrong. Try again in a minute.");
          if (r.status === 429) { input.disabled = true; send.disabled = true; return; }
        } else {
          const note = data.voice === "withheld" ? "(not spoken: I don't read out words people hand me)"
            : data.voice === "on" ? null : "(voice unavailable right now)";
          say("assistant", data.reply, note);
          history.push({ role: "user", content: text }, { role: "assistant", content: data.reply });
          if (data.voice === "on" && data.audio_b64 && data.alignment) {
            speak(data.audio_b64, data.alignment).catch(() => stopSpeaking());
          }
        }
      } catch (e) {
        thinking.remove();
        say("assistant", "I can't reach the server right now. Try again in a minute.");
      } finally {
        root.classList.remove("aid-busy");
        if (!input.disabled) { send.disabled = false; input.focus(); }
      }
    });

    return { stop: stopSpeaking };
  }

  window.AIDavid = { mount };
})();
