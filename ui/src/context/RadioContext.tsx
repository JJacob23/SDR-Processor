import React, { createContext, useContext, useEffect, useRef, useState } from "react";

export type RadioCtx = {
  // classifier data
  prediction: string | null;
  confidence: number | null;

  // FSM visualization
  activeNode: string | null;
  activeEdge: string | null;

  // audio feedback
  audioLevel: number;
  isMuted: boolean;
  setIsMuted: React.Dispatch<React.SetStateAction<boolean>>;
};

const RadioContext = createContext<RadioCtx | undefined>(undefined);


export const useRadio = (): RadioCtx => {
  const ctx = useContext(RadioContext);
  if (!ctx) throw new Error("useRadio must be used within a RadioProvider");
  return ctx;
};

export const RadioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [prediction, setPrediction] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [activeEdge, _setActiveEdge] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [isMuted, setIsMuted] = useState(false);

  const wsStateRef = useRef<WebSocket | null>(null);
  const wsPredRef = useRef<WebSocket | null>(null);
  const wsAudioRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (wsStateRef.current || wsPredRef.current || wsAudioRef.current) return;

    const wsState = new WebSocket("ws://localhost:8000/ws/state");
    const wsPred = new WebSocket("ws://localhost:8000/ws/classifier");
    const wsAudio = new WebSocket("ws://localhost:8000/ws/audio");
    wsAudio.binaryType = "arraybuffer"; 


    wsState.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setActiveNode(String(msg.station));
    };

    wsPred.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setPrediction(msg.label);
      if (msg.probs) setConfidence(Math.max(...msg.probs));
    };

    wsAudio.onmessage = (e) => {
      // calculate RMS level
      const buf = new Float32Array(e.data as ArrayBuffer);
      const rms =
        Math.sqrt(buf.reduce((sum, v) => sum + v * v, 0) / buf.length) || 0;
      setAudioLevel(rms);
    };

    wsStateRef.current = wsState;
    wsPredRef.current = wsPred;
    wsAudioRef.current = wsAudio;

    return () => {
      wsState.close();
      wsPred.close();
      wsAudio.close();
    };
  }, []);

  return (
    <RadioContext.Provider
      value={{
        prediction,
        confidence,
        activeNode,
        activeEdge,
        audioLevel,
        isMuted,
        setIsMuted,
      }}
    >
      {children}
    </RadioContext.Provider>
  );
};

