import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";
import { useRadio } from "../context/RadioContext";

/**
 * AudioVisualizer
 * Plays and visualizes live audio chunks from RadioContext.
 */
export default function AudioVisualizer() {
  // now only using audioLevel + isMuted (no undefined audioBuffer)
  const { audioLevel, isMuted } = useRadio();
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  /* ─────── One-time WaveSurfer setup ─────── */
  useEffect(() => {
    if (!containerRef.current) return;

    const wave = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#00ff00",
      progressColor: "#00ff00",
      cursorColor: "#00ff00",
      height: 150,
      normalize: true,
      interact: false,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
    });

    wavesurferRef.current = wave;
    audioCtxRef.current = new AudioContext();

    // Resume context after user gesture (Firefox autoplay block)
    const resumeAudio = () => {
      if (audioCtxRef.current?.state === "suspended") {
        audioCtxRef.current.resume();
      }
      window.removeEventListener("click", resumeAudio);
    };
    window.addEventListener("click", resumeAudio);

    return () => {
      wave.destroy();
      audioCtxRef.current?.close();
    };
  }, []);

  /* ─────── Optional: animate color with RMS level ─────── */
  useEffect(() => {
    const wave = wavesurferRef.current;
    if (!wave) return;
    const brightness = Math.min(1, Math.max(0, audioLevel));
    const green = Math.floor(180 + 75 * brightness);
    wave.setOptions({
      waveColor: `rgb(${green},255,${green})`,
      progressColor: `rgb(${green},255,${green})`,
    });
  }, [audioLevel]);

  return (
    <div
      ref={containerRef}
      className={`w-full h-40 border border-gray-700 rounded-lg ${
        isMuted ? "bg-gray-800/70" : "bg-black/50"
      }`}
    />
  );
}

/* ---------- helper: AudioBuffer → WAV blob ---------- 
async function bufferToWav(buffer: AudioBuffer): Promise<Blob> {
  const numOfChan = buffer.numberOfChannels;
  const length = buffer.length * numOfChan * 2 + 44;
  const bufferArray = new ArrayBuffer(length);
  const view = new DataView(bufferArray);
  const channels: Float32Array[] = [];
  const sampleRate = buffer.sampleRate;
  const bitDepth = 16;

  writeUTFBytes(view, 0, "RIFF");
  view.setUint32(4, 36 + buffer.length * numOfChan * 2, true);
  writeUTFBytes(view, 8, "WAVE");
  writeUTFBytes(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numOfChan, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2 * numOfChan, true);
  view.setUint16(32, numOfChan * 2, true);
  view.setUint16(34, bitDepth, true);
  writeUTFBytes(view, 36, "data");
  view.setUint32(40, buffer.length * numOfChan * 2, true);

  let offset = 44;
  for (let i = 0; i < numOfChan; i++) channels.push(buffer.getChannelData(i));
  for (let i = 0; i < buffer.length; i++)
    for (let c = 0; c < numOfChan; c++) {
      const sample = Math.max(-1, Math.min(1, channels[c][i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }

  return new Blob([view], { type: "audio/wav" });
}

function writeUTFBytes(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
}
*/
