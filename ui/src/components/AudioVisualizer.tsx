import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";
import { useRadio } from "../context/RadioContext";

/**
 * WaveSurfer waveform (top) + Spectrogram (bottom with Y-axis)
 * - Taller waveform & spectrogram
 * - Left frequency axis for spectrogram
 */
export default function AudioVisualizer() {
  const { isMuted, audioLevel } = useRadio();

  // -------- Waveform (WaveSurfer) --------
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);

  // -------- Audio pipeline --------
  const SAMPLE_RATE = 48000; // matches your FM audio sink
  const audioCtxRef = useRef<AudioContext | null>(null);
  const gainRef = useRef<GainNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const nextStartRef = useRef<number>(0); // scheduling cursor in AudioContext time

  // Ring buffer for the last N seconds (visualization window)
  const WINDOW_SEC = 5; // waveform window
  const RING_CAP = SAMPLE_RATE * WINDOW_SEC;
  const ringRef = useRef<Float32Array>(new Float32Array(RING_CAP));
  const ringWriteRef = useRef<number>(0);
  const ringFillRef = useRef<number>(0);

  // -------- Spectrogram (axis + canvas) --------
  const specWrapRef = useRef<HTMLDivElement>(null);
  const axisCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const specCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const specRAF = useRef<number | null>(null);
  const specBinsRef = useRef<Uint8Array | null>(null);

  /** Initialize WaveSurfer once */
  useEffect(() => {
    if (!containerRef.current) return;
    const ws = WaveSurfer.create({
      container: containerRef.current,
      backend: "WebAudio",
      height: 180,           // ⬆ taller waveform
      barWidth: 0,
      cursorWidth: 0,
      normalize: true,
      interact: false,
      waveColor: "#68f0a5",
      progressColor: "#68f0a5",
    });
    wavesurferRef.current = ws;
    return () => {
      ws.destroy();
      wavesurferRef.current = null;
    };
  }, []);

  /** Initialize AudioContext / Gain / Analyser once */
  useEffect(() => {
    if (!audioCtxRef.current) {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: SAMPLE_RATE,
      });
      const gain = ctx.createGain();
      gain.gain.value = isMuted ? 0 : 1;
      gain.connect(ctx.destination);

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048; // 1024 bins
      analyser.smoothingTimeConstant = 0.8;

      audioCtxRef.current = ctx;
      gainRef.current = gain;
      analyserRef.current = analyser;
      nextStartRef.current = ctx.currentTime + 0.1; // small lead to avoid underruns
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Apply mute updates immediately */
  useEffect(() => {
    if (gainRef.current) gainRef.current.gain.value = isMuted ? 0 : 1;
  }, [isMuted]);

  /** Helper: append chunk to ring buffer */
  const pushToRing = (chunk: Float32Array) => {
    const ring = ringRef.current;
    let w = ringWriteRef.current;
    let filled = ringFillRef.current;

    for (let i = 0; i < chunk.length; i++) {
      ring[w] = chunk[i];
      w = (w + 1) % RING_CAP;
      if (filled < RING_CAP) filled++;
    }
    ringWriteRef.current = w;
    ringFillRef.current = filled;
  };

  /** Helper: export current ring contents in time order */
  const exportRing = (): Float32Array => {
    const ring = ringRef.current;
    const filled = ringFillRef.current;
    if (filled === 0) return new Float32Array(0);

    const start = (ringWriteRef.current - filled + RING_CAP) % RING_CAP;
    const out = new Float32Array(filled);
    if (start + filled <= RING_CAP) {
      out.set(ring.subarray(start, start + filled), 0);
    } else {
      const firstLen = RING_CAP - start;
      out.set(ring.subarray(start, RING_CAP), 0);
      out.set(ring.subarray(0, filled - firstLen), firstLen);
    }
    return out;
  };

  /** Throttled waveform redraw (kept as-is) */
  const lastDrawRef = useRef<number>(0);
  const maybeRedrawWave = () => {
    const now = performance.now();
    if (now - lastDrawRef.current < 150) return; // ~6 FPS is enough for a rolling wave
    lastDrawRef.current = now;

    const ws = wavesurferRef.current;
    const ctx = audioCtxRef.current;
    if (!ws || !ctx) return;

    const samples = exportRing();
    if (samples.length === 0) return;

    const buf = ctx.createBuffer(1, samples.length, SAMPLE_RATE);
    buf.getChannelData(0).set(samples);
    const durationSec = samples.length / SAMPLE_RATE;

    wavesurferRef.current!
      .load("", [samples], durationSec)
      .catch(() => {});
  };

  /** Open the /ws/audio socket, stream PCM, schedule playback, and draw */
  useEffect(() => {
    const url =
      (location.protocol === "https:" ? "wss://" : "ws://") +
      location.host +
      "/ws/audio";
    const sock = new WebSocket(url);
    sock.binaryType = "arraybuffer";
    wsRef.current = sock;

    sock.onmessage = (ev) => {
      if (!(ev.data instanceof ArrayBuffer)) return;
      const f32 = new Float32Array(ev.data);

      // 1) Playback scheduling
      const ctx = audioCtxRef.current!;
      const gain = gainRef.current!;
      const analyser = analyserRef.current!;

      const buf = ctx.createBuffer(1, f32.length, SAMPLE_RATE);
      buf.getChannelData(0).set(f32);
      const src = ctx.createBufferSource();
      src.buffer = buf;

      // fan-out: audible + analyser (for spectrogram)
      src.connect(gain);
      src.connect(analyser);

      const now = ctx.currentTime;
      const startAt = Math.max(nextStartRef.current, now + 0.02);
      src.start(startAt);
      nextStartRef.current = startAt + buf.duration;

      // 2) Visualization
      pushToRing(f32);
      maybeRedrawWave();
    };

    sock.onerror = () => {};
    sock.onclose = () => { wsRef.current = null; };

    return () => {
      try { sock.close(); } catch {}
    };
  }, []); // mount once

  /** Waveform tint follows audioLevel (kept) */
  useEffect(() => {
    const wave = wavesurferRef.current;
    if (!wave) return;
    const brightness = Math.min(1, Math.max(0, audioLevel));
    const g = Math.floor(180 + 75 * brightness);
    wave.setOptions({
      waveColor: `rgb(${g},255,${g})`,
      progressColor: `rgb(${g},255,${g})`,
    });
  }, [audioLevel]);

  // --------- Spectrogram: size & draw (with Y-axis) ---------
  useEffect(() => {
    const holder = specWrapRef.current;
    const axis = axisCanvasRef.current;
    const canvas = specCanvasRef.current;
    if (!holder || !axis || !canvas) return;

    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const AXIS_W = 44; // px gutter for labels

    const sizeUp = () => {
      const { width, height } = holder.getBoundingClientRect();

      // axis canvas
      axis.style.width = `${AXIS_W}px`;
      axis.style.height = `${height}px`;
      axis.width = Math.max(1, Math.floor(AXIS_W * dpr));
      axis.height = Math.max(1, Math.floor(height * dpr));

      // spectrogram canvas (remaining width)
      const specW = Math.max(1, width - AXIS_W);
      canvas.style.width = `${specW}px`;
      canvas.style.height = `${height}px`;
      canvas.width = Math.max(1, Math.floor(specW * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));

      // redraw axis
      const ctxAxis = axis.getContext("2d");
      if (ctxAxis) drawAxis(ctxAxis, axis.width, axis.height, dpr, SAMPLE_RATE);
    };

    sizeUp();
    const ro = new ResizeObserver(sizeUp);
    ro.observe(holder);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const canvas = specCanvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx2d = canvas.getContext("2d", { alpha: false });
    if (!ctx2d) return;

    const bins = analyser.frequencyBinCount; // fftSize/2
    if (!specBinsRef.current || specBinsRef.current.length !== bins) {
      specBinsRef.current = new Uint8Array(bins);
    }

    // color palette
    const colorFor = (v: number) => {
      const p = v / 255;      // 0..1
      const h = (1 - p) * 240;// blue->red
      const l = 10 + p * 50;  // 10%..60%
      return `hsl(${h}, 100%, ${l}%)`;
    };

    const draw = () => {
      specRAF.current = requestAnimationFrame(draw);

      analyser.getByteFrequencyData(specBinsRef.current!);

      const W = canvas.width;
      const H = canvas.height;

      // scroll left by 1px
      ctx2d.drawImage(canvas, 1, 0, W - 1, H, 0, 0, W - 1, H);

      // draw new column at right edge
      const x = W - 1;
      const arr = specBinsRef.current!;
      const step = arr.length / H;

      for (let y = 0; y < H; y++) {
        const idx = Math.min(arr.length - 1, Math.floor(y * step));
        const v = arr[idx];
        ctx2d.fillStyle = colorFor(v);
        ctx2d.fillRect(x, H - 1 - y, 1, 1); // low freqs at bottom
      }
    };

    specRAF.current = requestAnimationFrame(draw);
    return () => { if (specRAF.current) cancelAnimationFrame(specRAF.current); };
  }, []);

  // --------- UI (taller + axis) ---------
  return (
    <div className="w-full border border-gray-700 rounded-lg overflow-hidden">
      {/* Waveform (top) - taller */}
      <div
        ref={containerRef}
        className={`w-full h-56 ${isMuted ? "bg-gray-800/70" : "bg-gray-900/70"}`}
      />
      {/* Spectrogram (bottom) - taller + Y-axis */}
      <div ref={specWrapRef} className="w-full h-40 bg-black/60 flex">
        <canvas ref={axisCanvasRef} className="block" />
        <canvas ref={specCanvasRef} className="block flex-1" />
      </div>
    </div>
  );
}

/* ===== helpers ===== */
function drawAxis(
  ctx: CanvasRenderingContext2D,
  W: number,
  H: number,
  dpr: number,
  sampleRate = 48000
) {
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.fillRect(0, 0, W, H);

  // axis line
  ctx.strokeStyle = "rgba(255,255,255,0.15)";
  ctx.lineWidth = 1 * dpr;
  ctx.beginPath();
  ctx.moveTo(W - 1 * dpr, 0);
  ctx.lineTo(W - 1 * dpr, H);
  ctx.stroke();

  // ticks + labels (linear 0..Nyquist)
  const nyquist = sampleRate / 2;
  const ticks = 6;
  ctx.fillStyle = "rgba(255,255,255,0.75)";
  ctx.font = `${11 * dpr}px ui-monospace, SFMono-Regular, Menlo, monospace`;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  for (let i = 0; i < ticks; i++) {
    const frac = i / (ticks - 1);       // 0..1
    const y = H - Math.round(frac * H); // low at bottom
    const hz = frac * nyquist;
    const label = hz >= 1000 ? `${(hz / 1000).toFixed(0)}k` : `${hz.toFixed(0)}`;

    // tick
    ctx.strokeStyle = "rgba(255,255,255,0.25)";
    ctx.beginPath();
    ctx.moveTo(W - 8 * dpr, y);
    ctx.lineTo(W - 1 * dpr, y);
    ctx.stroke();

    // text
    ctx.fillText(label, W - 10 * dpr, y);
  }
}

