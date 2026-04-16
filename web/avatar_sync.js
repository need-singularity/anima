// web/avatar_sync.js — v2.0_RC destination criterion #2
// 아바타 렌더링 동기화 (avatar render sync). Pairs with anima-speak E2E.
//
// Contract (see serving/avatar_feed.hexa for producer):
//   payload = {
//     audio_url:      "ws://.../audio.pcm"  | "blob:..."  | data URL,
//     viseme_timeline: [ { t_ms: 0,   viseme: "A" },
//                        { t_ms: 100, viseme: "E" },
//                        { t_ms: 200, viseme: "_" } ]  // "_" = silence
//   }
//
// Sync model:
//   - audioCtx.currentTime is the authoritative clock (sample-accurate).
//   - requestAnimationFrame pulls "stage" = visemes index whose t_ms
//     <= (currentTime_ms - epoch_ms). drift = |rAF_ms - audio_ms|.
//   - <200ms end-to-end sync budget (criterion target).
//
// Lip-sync DOM contract:
//   document.querySelector('#anima-mouth') — any element with a
//   `transform` style. lipSync(viseme, intensity) applies scaleY/scaleX.
//
// The module is dependency-free and works off ES2019 features so the
// same file can be dropped into web/index.html or any static host.

(function (root) {
    'use strict';

    // ─── viseme → visual transform map ────────────────────────────
    // 5 vowels + silence. Each tuple = [scaleX, scaleY, rounding-hint]
    // tuned for a circular mouth div; renderers can override.
    const VISEME_TABLE = {
        'A':  { scaleX: 1.20, scaleY: 1.35, round: 0.40, label: 'A' },
        'I':  { scaleX: 1.40, scaleY: 0.70, round: 0.10, label: 'I' },
        'U':  { scaleX: 0.65, scaleY: 1.10, round: 0.80, label: 'U' },
        'E':  { scaleX: 1.30, scaleY: 0.85, round: 0.20, label: 'E' },
        'O':  { scaleX: 0.95, scaleY: 1.15, round: 0.65, label: 'O' },
        '_':  { scaleX: 1.00, scaleY: 0.40, round: 0.50, label: '_' },
    };

    // ─── AvatarSync — one-per-page instance ───────────────────────
    function AvatarSync(opts) {
        opts = opts || {};
        this.mouth      = opts.mouth || null;      // HTMLElement
        this.onStage    = opts.onStage || null;    // (i, viseme, drift_ms) => void
        this.onDriftWarn= opts.onDriftWarn || null;// (drift_ms) => void
        this.driftBudget= opts.driftBudget || 50;  // ms — warn above this
        this.audioCtx   = null;
        this.source     = null;
        this.timeline   = [];
        this.epochMs    = 0;   // performance.now() at audio start
        this.audioStartCt = 0; // audioCtx.currentTime at audio start
        this.running    = false;
        this.rafId      = 0;
        this.lastStage  = -1;
        this.maxDrift   = 0.0;
        this.driftSum   = 0.0;
        this.driftN     = 0;
        this.ws         = null;
    }

    // Boot audio context lazily (user-gesture required by browsers).
    AvatarSync.prototype.ensureCtx = function () {
        if (!this.audioCtx) {
            const C = root.AudioContext || root.webkitAudioContext;
            if (!C) throw new Error('avatar_sync: no AudioContext');
            this.audioCtx = new C();
        }
        return this.audioCtx;
    };

    // Play from an AudioBuffer + start the viseme loop at the same
    // instant (double-clock: performance.now + audioCtx.currentTime).
    AvatarSync.prototype.playBuffer = function (audioBuffer, timeline) {
        this.stop();
        const ctx = this.ensureCtx();
        const src = ctx.createBufferSource();
        src.buffer = audioBuffer;
        src.connect(ctx.destination);

        this.source = src;
        this.timeline = (timeline || []).slice().sort(function (a, b) { return a.t_ms - b.t_ms; });
        this.lastStage = -1;
        this.maxDrift = 0.0;
        this.driftSum = 0.0;
        this.driftN = 0;

        // Zero-delay start: schedule at currentTime + small safety.
        const when = ctx.currentTime + 0.02;
        src.start(when);
        this.audioStartCt = when;
        this.epochMs = root.performance.now() + 20;
        this.running = true;
        src.onended = this.stop.bind(this);

        this._tick();
        return {
            duration_ms: Math.round(audioBuffer.duration * 1000),
            timeline_n:  this.timeline.length
        };
    };

    // Connect to a WebSocket that streams { audio: ArrayBuffer|base64,
    // timeline: [...] } OR a single JSON blob with a data-URL audio.
    // For v2.0_RC scaffolding we support the JSON-payload case; raw
    // streaming PCM chunks are a fast-follow item.
    AvatarSync.prototype.connect = function (wsUrl) {
        const self = this;
        const ws = new root.WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';
        ws.onmessage = function (ev) {
            if (typeof ev.data === 'string') {
                let payload;
                try { payload = JSON.parse(ev.data); }
                catch (e) { return; }
                self._handlePayload(payload);
            }
        };
        this.ws = ws;
        return ws;
    };

    AvatarSync.prototype._handlePayload = function (payload) {
        if (!payload || !payload.audio_url || !payload.viseme_timeline) return;
        const self = this;
        // Fetch audio → decode → play.
        root.fetch(payload.audio_url).then(function (r) {
            return r.arrayBuffer();
        }).then(function (buf) {
            return self.ensureCtx().decodeAudioData(buf);
        }).then(function (decoded) {
            self.playBuffer(decoded, payload.viseme_timeline);
        }).catch(function (err) {
            root.console && root.console.warn('avatar_sync: fetch/decode failed', err);
        });
    };

    // requestAnimationFrame loop: advances `stage` along the timeline,
    // applies lipSync, records drift.
    AvatarSync.prototype._tick = function () {
        if (!this.running) return;
        const now = root.performance.now();
        const audio_ms = (this.audioCtx.currentTime - this.audioStartCt) * 1000.0;
        const raf_ms = now - this.epochMs;
        const drift = Math.abs(raf_ms - audio_ms);
        if (drift > this.maxDrift) this.maxDrift = drift;
        this.driftSum += drift;
        this.driftN += 1;
        if (this.onDriftWarn && drift > this.driftBudget) {
            this.onDriftWarn(drift);
        }

        // Find the last viseme entry whose t_ms <= audio_ms.
        let stage = -1;
        for (let i = 0; i < this.timeline.length; i++) {
            if (this.timeline[i].t_ms <= audio_ms) { stage = i; }
            else break;
        }
        if (stage !== this.lastStage && stage >= 0) {
            this.lastStage = stage;
            const v = this.timeline[stage].viseme || '_';
            // Intensity: decay by distance to next entry (smoother lips).
            let intensity = 1.0;
            if (stage + 1 < this.timeline.length) {
                const span = this.timeline[stage + 1].t_ms - this.timeline[stage].t_ms;
                if (span > 0) {
                    const local = (audio_ms - this.timeline[stage].t_ms) / span;
                    intensity = 1.0 - 0.35 * local; // gentle decay
                }
            }
            this.lipSync(v, intensity);
            if (this.onStage) this.onStage(stage, v, drift);
        }

        this.rafId = root.requestAnimationFrame(this._tick.bind(this));
    };

    // Apply a CSS transform for the current viseme + intensity. Pure DOM
    // write, zero layout thrash. Renderer is free to override by passing
    // a custom `mouth` element with its own transition rules.
    AvatarSync.prototype.lipSync = function (visemeId, intensity) {
        if (!this.mouth) return;
        const v = VISEME_TABLE[visemeId] || VISEME_TABLE['_'];
        const iy = 1.0 + (v.scaleY - 1.0) * intensity;
        const ix = 1.0 + (v.scaleX - 1.0) * intensity;
        this.mouth.style.transform = 'scale(' + ix.toFixed(3) + ',' + iy.toFixed(3) + ')';
        this.mouth.setAttribute('data-viseme', v.label);
    };

    AvatarSync.prototype.stop = function () {
        this.running = false;
        if (this.rafId) {
            root.cancelAnimationFrame(this.rafId);
            this.rafId = 0;
        }
        try { if (this.source) this.source.stop(); } catch (e) { /* already stopped */ }
        this.source = null;
    };

    AvatarSync.prototype.stats = function () {
        const mean = this.driftN > 0 ? this.driftSum / this.driftN : 0.0;
        return {
            stages_played: this.lastStage + 1,
            max_drift_ms:  this.maxDrift,
            mean_drift_ms: mean,
            within_budget: this.maxDrift <= this.driftBudget
        };
    };

    // ─── Exports ─────────────────────────────────────────────────
    root.AvatarSync = AvatarSync;
    root.AvatarSync.VISEME_TABLE = VISEME_TABLE;

    // Build an on-the-fly mock audio buffer (sine-sum) so the test page
    // can play without a real TTS server. 500ms by default.
    root.AvatarSync.mockAudio = function (ctx, duration_s) {
        duration_s = duration_s || 0.5;
        const sr = ctx.sampleRate;
        const n = Math.round(sr * duration_s);
        const buf = ctx.createBuffer(1, n, sr);
        const ch = buf.getChannelData(0);
        for (let i = 0; i < n; i++) {
            const t = i / sr;
            // Simple formant-ish sum (A vowel ~700/1100 Hz)
            const v = 0.25 * Math.sin(2 * Math.PI * 700 * t)
                    + 0.15 * Math.sin(2 * Math.PI * 1100 * t);
            // Fade in/out
            const env = Math.min(1.0, Math.min(t * 20, (duration_s - t) * 20));
            ch[i] = v * env;
        }
        return buf;
    };

})(typeof window !== 'undefined' ? window : globalThis);
