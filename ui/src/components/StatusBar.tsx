import React, { useEffect, useState } from "react";

export default function StatusBar() {
  const [label, setLabel] = useState("--");
  const [confidence, setConfidence] = useState(0);
  const [station, setStation] = useState(0);
  const [lag, setLag] = useState("--");

  useEffect(() => {
    const classifierWS = new WebSocket("ws://localhost:8000/ws/classifier");
    const stateWS = new WebSocket("ws://localhost:8000/ws/state");
    let lastTime = performance.now();
    let intervals: number[] = [];

    classifierWS.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setLabel(msg.label);
      setConfidence(Math.max(...msg.probs));
    };

    stateWS.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setStation(msg.station / 1e6);
    };

    const audioWS = new WebSocket("ws://localhost:8000/ws/audio");
    audioWS.binaryType = "arraybuffer";
    audioWS.onmessage = () => {
      const now = performance.now();
      const diff = now - lastTime;
      lastTime = now;
      intervals.push(diff);
      if (intervals.length > 50) intervals.shift();
      const avg = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      setLag(avg.toFixed(1));
    };

    return () => {
      classifierWS.close();
      stateWS.close();
      audioWS.close();
    };
  }, []);

  return (
    <div className="flex justify-between p-2 border-t border-gray-600 text-sm">
      <div>Station: {station.toFixed(3)} MHz</div>
      <div>Last: {label} ({confidence.toFixed(2)})</div>
      <div>Lag: {lag} ms</div>
    </div>
  );
}

