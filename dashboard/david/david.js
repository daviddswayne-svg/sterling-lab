// AI David: David's photo, lip-synced to his cloned voice, with a question box.
// Shared by the homepage widget (widget.js) and the /david/ page.
//   AIDavid.mount(element, { size: "widget" | "page" })
// Frames are LivePortrait renders of one photo (~/Projects/ai-david/gen_frames.py on the M3).
// The API (/api/david/chat) streams the reply, then one MP3 per sentence chunk with per-character
// timings from David's cloned voice on the M3. The reply is spoken, not shown (text only appears when
// there's no voice: muted, voice down, or withheld).
//
// Lip-sync: how OPEN the mouth is follows the loudness of the decoded audio (so it can't drift from the
// sound); the SHAPE comes from the vowel of the syllable being spoken; each shape is held >= HOLD so the
// mouth moves at syllable speed rather than letter speed. Times are shifted by the output latency so the
// mouth matches what is heard, not what is scheduled.
(function () {
  "use strict";
  const BASE = "/david/frames/";
  const FRAMES = ["rest", "mbp", "slight", "aa", "ee", "oh", "oo", "blink1", "blink2", "smile"];
  const MAX_HISTORY = 6;
  const ENV_STEP = 0.02;   // loudness envelope resolution (s)
  const HOLD = 0.09;       // minimum time a mouth shape stays up (s)
  const VOWEL_SHAPE = { a: "aa", e: "ee", i: "ee", y: "ee", o: "oh", u: "oo" };

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  // Per 20 ms loudness of a clip, 0..1 relative to its loud parts, lightly smoothed (fast open, slower close).
  function envelope(buffer) {
    const data = buffer.getChannelData(0);
    const step = Math.max(1, Math.round(buffer.sampleRate * ENV_STEP));
    const raw = [];
    for (let i = 0; i < data.length; i += step) {
      let sum = 0;
      const end = Math.min(data.length, i + step);
      for (let j = i; j < end; j++) sum += data[j] * data[j];
      raw.push(Math.sqrt(sum / (end - i)));
    }
    const sorted = raw.slice().sort((a, b) => a - b);
    const loud = sorted[Math.floor(sorted.length * 0.95)] || 1;
    let prev = 0;
    return raw.map((v) => {
      const x = Math.min(1, v / loud);
      prev = x > prev ? x : prev * 0.6 + x * 0.4;
      return prev;
    });
  }

  // For every character, the shape of the vowel its syllable is built around: the vowel at or after it
  // in the same word, else the one before it. Non-letters get null.
  function vowelShapes(chars) {
    const out = new Array(chars.length).fill(null);
    let i = 0;
    while (i < chars.length) {
      if (!/[a-z']/i.test(chars[i])) { i++; continue; }
      let j = i;
      while (j < chars.length && /[a-z']/i.test(chars[j])) j++;   // word = [i, j)
      let next = null;
      for (let k = j - 1; k >= i; k--) {
        const v = VOWEL_SHAPE[chars[k].toLowerCase()];
        if (v) next = v;
        out[k] = next;
      }
      let prev = null;
      for (let k = i; k < j; k++) {
        if (VOWEL_SHAPE[chars[k].toLowerCase()]) prev = out[k];
        if (!out[k]) out[k] = prev || "slight";
      }
      i = j;
    }
    return out;
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
    const status = el("div", "aid-status");
    face.append(head, status);

    const label = el("p", "aid-label");
    label.append(el("strong", null, "AI David"),
      " · an AI version of David Swayne, in his cloned voice. It can make mistakes.");

    // --- questions ---
    const log = el("div", "aid-log");
    log.append(el("p", "aid-hint", "Ask me about my work, the projects on this site, or anything really. I'll answer out loud."));
    const spoken = el("div", "aid-sr");     // screen readers still get every reply
    spoken.setAttribute("aria-live", "polite");
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

    root.append(face, label, log, spoken, form, meta);

    // --- state ---
    let shown = "rest";
    let speaking = false;
    let muted = false;
    let audioCtx = null;
    let gain = null;
    let talk = null;      // current reply: scheduled audio segments + their timings
    let talkId = 0;       // bumps on every new reply/stop so late segments of an old reply are dropped
    const history = [];

    function show(name) {
      if (name === shown) return;
      imgs[shown].classList.remove("on");
      imgs[name].classList.add("on");
      shown = name;
    }

    function setStatus(text) {
      status.textContent = text || "";
      status.classList.toggle("on", !!text);
    }

    function say(role, text, note) {
      const hint = log.querySelector(".aid-hint");
      if (hint) hint.remove();
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

    // Seconds between the audio clock and the speaker: the mouth follows what is heard.
    function latency() {
      return (audioCtx.outputLatency || 0) + (audioCtx.baseLatency || 0);
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

    // Each chunk is scheduled to start when the previous one ends; one animation loop drives the mouth.
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
      const chars = alignment.characters || [];
      talk.segs.push({
        t0, end: t0 + buffer.duration, i: 0, chars,
        starts: alignment.character_start_times_seconds || [],
        ends: alignment.character_end_times_seconds || [],
        env: envelope(buffer),
        vowel: vowelShapes(chars),
      });
      talk.endAt = t0 + buffer.duration;
      if (!speaking) {
        speaking = true;
        setStatus("");
        root.classList.add("aid-talking");
        requestAnimationFrame(() => tick(id));
      }
    }

    function mouthAt(seg, t) {
      const lvl = seg.env[Math.min(seg.env.length - 1, Math.max(0, Math.floor(t / ENV_STEP)))] || 0;
      while (seg.i < seg.chars.length - 1 && seg.ends[seg.i] <= t) seg.i++;
      const ch = (seg.chars[seg.i] || "").toLowerCase();
      const inChar = t >= seg.starts[seg.i] && t < seg.ends[seg.i];
      if (inChar && "mbp".includes(ch) && lvl < 0.5) return "mbp";   // lips close on M/B/P
      if (lvl < 0.12) return "rest";
      const vowel = (inChar && seg.vowel[seg.i]) || "slight";
      if (lvl < 0.35) return vowel === "oh" || vowel === "oo" ? "oo" : "slight";
      return vowel === "slight" ? "slight" : vowel;
    }

    function tick(id) {
      if (id !== talkId || !talk) return;
      const heard = audioCtx.currentTime - latency();
      if (talk.done && heard >= talk.endAt) { finishTalking(); return; }
      const seg = talk.segs.find((s) => heard >= s.t0 && heard < s.end);
      const want = seg ? mouthAt(seg, heard - seg.t0) : "rest";
      if (want !== talk.current && heard - talk.since >= HOLD) {
        talk.current = want;
        talk.since = heard;
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
      setStatus("thinking…");
      send.disabled = true;
      root.classList.add("aid-busy");
      let reply = null;
      let shownAsText = false;
      const showText = (note) => {
        if (reply && !shownAsText) { shownAsText = true; say("assistant", reply, note); }
      };
      try {
        const r = await fetch("/api/david/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, history: history.slice(-MAX_HISTORY) }),
        });
        if (!r.ok) {
          const data = await r.json().catch(() => ({}));
          setStatus("");
          if (typeof data.remaining === "number") remainingText(data.remaining);
          say("assistant", data.error || "Something went wrong. Try again in a minute.");
          if (r.status === 429) { input.disabled = true; send.disabled = true; }
          return;
        }
        // NDJSON: {reply, remaining, voice} first, then {seg, audio_b64, alignment} per chunk, then {done}.
        const reader = r.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        let voiceOk = true;
        const handle = async (line) => {
          const d = JSON.parse(line);
          if (d.reply != null) {
            reply = d.reply;
            spoken.textContent = reply;
            if (typeof d.remaining === "number") remainingText(d.remaining);
            history.push({ role: "user", content: text }, { role: "assistant", content: reply });
            if (d.voice === "withheld") { voiceOk = false; setStatus(""); showText("(not spoken: I don't read out words people hand me)"); }
            else if (muted) showText("(sound is off)");
          } else if (d.audio_b64 && d.alignment && voiceOk) {
            await enqueue(id, d.audio_b64, d.alignment).catch(() => {});
          } else if (d.voice === "error") {
            voiceOk = false;
            if (!talk) setStatus("");
            showText("(voice unavailable right now)");
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
        if (!talk) setStatus("");
        if (!reply) say("assistant", "Something went wrong. Try again in a minute.");
      } catch (e) {
        setStatus("");
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
