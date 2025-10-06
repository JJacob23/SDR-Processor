import React, { createContext, useContext, useEffect, useState } from "react";

interface RadioContextType {
  activeNode: string;
  activeEdge: string | null;
  lastEvent: "Ad" | "Song" | null;
  prediction: string | null;
  confidence: number | null;
  audioLevel: number;  // e.g. RMS or normalized
  audioBuffer: Float32Array | null;
  isMuted: boolean;
  setIsMuted: React.Dispatch<React.SetStateAction<boolean>>;
}

const RadioContext = createContext<RadioContextType>({
  activeNode: "primary",
  activeEdge: null,
  lastEvent: null,
  prediction: null,
  confidence: null,
  audioLevel: 0,
  audioBuffer: null,
  isMuted: false,
  setIsMuted: () => {},
});

export const useRadio = () => useContext(RadioContext);

export const RadioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeNode, setActiveNode] = useState<string>("primary");
  const [activeEdge, setActiveEdge] = useState<string | null>(null);
  const [lastEvent, setLastEvent] = useState<"Ad" | "Song" | null>(null);
  const [prediction, setPrediction] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [audioBuffer, setAudioBuffer] = useState<Float32Array | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(false); 

  useEffect(() => {
    // State / FSM socket
    const wsState = new WebSocket("ws://localhost:8000/ws/state");
    wsState.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event) setLastEvent(msg.event);
        if (msg.node) setActiveNode(msg.node);
        if (msg.edge) setActiveEdge(msg.edge);
      } catch (err) {
        console.error("[wsState] parse error:", err);
      }
    };
    wsState.onclose = () => console.log("[wsState] closed");

    // Prediction socket
    const wsPred = new WebSocket("ws://localhost:8000/ws/prediction");
    wsPred.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.label) setPrediction(msg.label);
        if (typeof msg.confidence === "number") setConfidence(msg.confidence);
      } catch (err) {
        console.error("[wsPred] parse error:", err);
      }
    };
    wsPred.onclose = () => console.log("[wsPred] closed");

    // Audio socket
    const wsAudio = new WebSocket("ws://localhost:8000/ws/audio");
    wsAudio.binaryType = "arraybuffer";
    wsAudio.onmessage = (ev) => {
      try {
        const float32 = new Float32Array(ev.data);
        setAudioBuffer(float32);
        const rms = Math.sqrt(float32.reduce((s, v) => s + v * v, 0) / float32.length);
        setAudioLevel(rms);
      } catch (err) {
        console.error("[wsAudio] parse error:", err);
      }
    };
    wsAudio.onclose = () => console.log("[wsAudio] closed");

    // Clean up all sockets on unmount
    return () => {
      wsState.close();
      wsPred.close();
      wsAudio.close();
    };
  }, []);

  return (
    <RadioContext.Provider
      value={{
        activeNode,
        activeEdge,
        lastEvent,
        prediction,
        confidence,
        audioLevel,
        audioBuffer,
        isMuted,
        setIsMuted,
      }}
    >
      {children}
    </RadioContext.Provider>
  );
};
