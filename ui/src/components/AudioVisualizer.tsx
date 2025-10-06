import React, { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";
import { useRadio } from "../context/RadioContext";

/**
 * AudioVisualizer
 * Plays and visualizes live audio chunks from RadioContext.
 */
export default function AudioVisualizer() {
  const { audioBuffer, audioLevel, isMuted } = useRadio();
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // one-time WaveSurfer + AudioContext setup
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

    return () => {
      wave.destroy();
      audioCtxRef.current?.close();
    };
  }, []);


    useEffect(() => {
    if (!audioBuffer || !audioCtxRef.current || !wavesurferRef.current) return;
    if (isMuted) return; // 👈 don't play if muted

    const audioCtx = audioCtxRef.current;
    const buf = audioCtx.createBuffer(1, audioBuffer.length, 48_000);
    buf.copyToChannel(audioBuffer as unknown as Float32Array<ArrayBuffer>, 0);



    const src = audioCtx.createBufferSource();
    src.buffer = buf;
    src.connect(audioCtx.destination);
    src.start();

    bufferToWav(buf).then((blob) => {
        const url = URL.createObjectURL(blob);
        wavesurferRef.current!.load(url);
    });
    }, [audioBuffer, isMuted]);

  // optional: pulse color with RMS
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
      className="w-full h-40 bg-black/50 border border-gray-700 rounded-lg"
    ></div>
  );
}

/* ---------- helper: AudioBuffer → WAV blob ---------- */
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
      let sample = Math.max(-1, Math.min(1, channels[c][i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }

  return new Blob([view], { type: "audio/wav" });
}

function writeUTFBytes(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
}
