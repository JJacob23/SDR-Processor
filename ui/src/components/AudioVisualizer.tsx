import React, { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";

export default function AudioVisualizer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const waveRef = useRef<WaveSurfer | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    waveRef.current = WaveSurfer.create({
      container: containerRef.current,
      waveColor: "#00ff00",
      progressColor: "#00ff00",
      cursorColor: "#00ff00",
      height: 150,
      interact: false,
      normalize: true,
    });

    wsRef.current = new WebSocket("ws://localhost:8000/ws/audio");
    wsRef.current.binaryType = "arraybuffer";

    wsRef.current.onmessage = (e) => {
      const audioBuffer = new Float32Array(e.data);
      const blob = new Blob([audioBuffer], { type: "audio/wav" });
      const url = URL.createObjectURL(blob);
      waveRef.current?.load(url);
    };

    return () => {
      wsRef.current?.close();
      waveRef.current?.destroy();
    };
  }, []);

  return <div ref={containerRef} className="w-full h-40"></div>;
}

