// AI David: David's photo, lip-synced to his cloned voice, with a chat box.
// Shared by the homepage widget (widget.js) and the /david/ page.
//   AIDavid.mount(element, { size: "widget" | "page" })
// Frames are LivePortrait renders of one photo (~/Projects/ai-david/gen_frames.py on the M3).
// The API (/api/david/chat) streams the reply text, then one MP3 per sentence with per-character
// timings from David's cloned voice on the M3; on every animation frame we look up the character
// being spoken and show its mouth shape.
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
    let talk = null;      // current reply: scheduled audio segments + their letter timings
    let talkId = 0;       // bumps on every new reply/stop so late segments of an old reply are dropped
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
      talkId++;
      if (talk) talk.sources.forEach((src) => { try { src.stop(); } catch (e) { /* already stopped */ } });
      talk = null;
      speaking = false;
      root.classList.remove("aid-talking");
      show("rest");
    }

    function finishTalking() {
      talk = null;
      speaking = false;
      root.classList.remove("aid-talking");
      show("smile");
      setTimeout(() => { if (!speaking && shown === "smile") show("rest"); }, 1200);
    }

    // The reply arrives one sentence at a time; each clip is scheduled to start when the previous ends,
    // and one animation loop picks the mouth shape from whichever clip is playing.
    async function enqueue(id, b64, alignment) {
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      const buffer = await audioCtx.decodeAudioData(bytes.buffer);
      if (id !== talkId) return;
      if (!talk) talk = { segs: [], sources: [], endAt: 0, done: false, current: "rest", since: 0 };
      const t0 = Math.max(audioCtx.currentTime + 0.05, talk.endAt);
      const src = audioCtx.createBufferSource();
      src.buffer = buffer;
      src.connect(gain);
      src.start(t0);
      talk.sources.push(src);
      talk.segs.push({
        t0, end: t0 + buffer.duration, i: 0,
        chars: alignment.characters || [],
        starts: alignment.character_start_times_seconds || [],
        ends: alignment.character_end_times_seconds || [],
      });
      talk.endAt = t0 + buffer.duration;
      if (!speaking) {
        speaking = true;
        root.classList.add("aid-talking");
        requestAnimationFrame(() => tick(id));
      }
    }

    function tick(id) {
      if (id !== talkId || !talk) return;
      const now = audioCtx.currentTime;
      if (talk.done && now >= talk.endAt) { finishTalking(); return; }
      const seg = talk.segs.find((s) => now >= s.t0 && now < s.end);
      let want = "rest";
      if (seg) {
        const t = now - seg.t0;
        while (seg.i < seg.chars.length - 1 && seg.ends[seg.i] <= t) seg.i++;
        if (t >= seg.starts[seg.i] && t < seg.ends[seg.i]) want = visemeFor(seg.chars[seg.i]);
      }
      // Hold each shape ~60 ms so fast letters don't flicker.
      if (want !== talk.current && now - talk.since > 0.06) {
        talk.current = want;
        talk.since = now;
        show(want);
      }
      requestAnimationFrame(() => tick(id));
    }

    function remainingText(n) {
      left.textContent = n + " question" + (n === 1 ? "" : "s") + " left today";
    }

    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const text = input.value.trim();
      if (!text || send.disabled) return;
      ensureAudio();
      stopSpeaking();
      const id = talkId;
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
        if (!r.ok) {
          const data = await r.json().catch(() => ({}));
          thinking.remove();
          if (typeof data.remaining === "number") remainingText(data.remaining);
          say("assistant", data.error || "Something went wrong. Try again in a minute.");
          if (r.status === 429) { input.disabled = true; send.disabled = true; }
          return;
        }
        // NDJSON: {reply, remaining, voice} first, then {seg, audio_b64, alignment} per sentence, then {done}.
        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        let msg = null;
        let voiceOk = true;
        const handle = async (line) => {
          const d = JSON.parse(line);
          if (d.reply != null) {
            thinking.remove();
            if (typeof d.remaining === "number") remainingText(d.remaining);
            const note = d.voice === "withheld" ? "(not spoken: I don't read out words people hand me)" : null;
            msg = say("assistant", d.reply, note);
            history.push({ role: "user", content: text }, { role: "assistant", content: d.reply });
          } else if (d.audio_b64 && d.alignment && voiceOk) {
            await enqueue(id, d.audio_b64, d.alignment).catch(() => {});
          } else if (d.voice === "error") {
            voiceOk = false;
            if (msg) msg.append(el("span", "aid-note", "(voice unavailable right now)"));
          } else if (d.done) {
            if (talk && id === talkId) talk.done = true;
          }
        };
        for (;;) {
          const { value, done } = await reader.read();
          if (value) buf += decoder.decode(value, { stream: true });
          let nl;
          while ((nl = buf.indexOf("\n")) >= 0) {
            const line = buf.slice(0, nl).trim();
            buf = buf.slice(nl + 1);
            if (line) await handle(line);
          }
          if (done) break;
        }
        if (buf.trim()) await handle(buf.trim());
        if (talk && id === talkId) talk.done = true;
        if (!msg) { thinking.remove(); say("assistant", "Something went wrong. Try again in a minute."); }
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
