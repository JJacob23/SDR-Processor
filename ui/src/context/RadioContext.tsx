import React, { createContext, useContext, useEffect, useRef, useState } from "react";

export type RadioCtx = {
  // classifier
  prediction: string | null;
  confidence: number | null;
  activeTransition: string | null; // e.g., "ad" / "song" (for edge highlighting)

  // FSM
  fsmState: string | null;         // "primary" | "patience1" | "patience2" | "secondary"
  station: string | number | null; // raw tuned station (Hz, usually a numeric string)

  // legacy names the UI used before (still exposed so existing code doesn't break)
  activeNode: string | null;
  activeEdge: string | null;

  // audio feedback
  audioLevel: number;
  isMuted: boolean;
  setIsMuted: React.Dispatch<React.SetStateAction<boolean>>;
};

const RadioContext = createContext<RadioCtx>({
  prediction: null,
  confidence: null,
  activeTransition: null,

  fsmState: null,
  station: null,

  activeNode: null,
  activeEdge: null,

  audioLevel: 0,
  isMuted: false,
  setIsMuted: () => {},
});

export const useRadio = () => useContext(RadioContext);

export function RadioProvider({ children }: { children: React.ReactNode }) {
  const [prediction, setPrediction] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [activeTransition, setActiveTransition] = useState<string | null>(null);

  const [fsmState, setFsmState] = useState<string | null>(null);
  const [station, setStation] = useState<string | number | null>(null);

  // legacy (kept for compatibility with components that still read these)
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [activeEdge, setActiveEdge] = useState<string | null>(null);

  const [audioLevel, setAudioLevel] = useState(0);
  const [isMuted, setIsMuted] = useState(false);

  const wsStateRef = useRef<WebSocket | null>(null);
  const wsPredRef  = useRef<WebSocket | null>(null);
  const wsAudioRef = useRef<WebSocket | null>(null);

  // --- helpers
  const url = (path: string) =>
    (location.protocol === "https:" ? "wss://" : "ws://") + location.host + path;

  // ----- STATE socket (/ws/state) -----
  useEffect(() => {
    const ws = new WebSocket(url("/ws/state"));
    wsStateRef.current = ws;

    ws.onopen = () => console.log("[WS state] open");
    ws.onclose = () => console.log("[WS state] close");
    ws.onerror = (e) => console.warn("[WS state] error", e as any);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(typeof e.data === "string" ? e.data : "");
        console.log("[WS state] msg", msg);
        // expected from backend: { state: "primary", station: 101100000 }
        if (typeof msg?.state === "string") {
          setFsmState(msg.state);
          setActiveNode(msg.state); // legacy mirror so older components still work
        }
        if (typeof msg?.station === "number" || typeof msg?.station === "string") {
          setStation(msg.station);
        }
      } catch (err) {
        console.warn("[WS state] bad payload", err);
      }
    };

    return () => { try { ws.close(); } catch {} };
  }, []);

  // ----- CLASSIFIER socket (/ws/classifier) -----
  useEffect(() => {
    const ws = new WebSocket(url("/ws/classifier"));
    wsPredRef.current = ws;

    ws.onopen = () => console.log("[WS classifier] open");
    ws.onclose = () => console.log("[WS classifier] close");
    ws.onerror = (e) => console.warn("[WS classifier] error", e as any);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(typeof e.data === "string" ? e.data : "");
        console.log("[WS classifier] msg", msg);
        // expected: { label: "ad"|"song"|..., probs: [ ... ] }
        if (typeof msg?.label === "string") {
          setPrediction(msg.label);
          setActiveTransition(msg.label.toLowerCase()); // used by FSM edge highlight
          setActiveEdge(msg.label.toLowerCase());       // legacy mirror
        }
        if (Array.isArray(msg?.probs)) {
          const m = Math.max(...msg.probs.map((x: any) => Number(x) || 0));
          setConfidence(Number.isFinite(m) ? m : null);
        }
      } catch (err) {
        console.warn("[WS classifier] bad payload", err);
      }
    };

    return () => { try { ws.close(); } catch {} };
  }, []);

  // ----- AUDIO socket (/ws/audio) -----
  useEffect(() => {
    const ws = new WebSocket(url("/ws/audio"));
    ws.binaryType = "arraybuffer";
    wsAudioRef.current = ws;

    ws.onopen = () => console.log("[WS audio] open");
    ws.onclose = () => console.log("[WS audio] close");
    ws.onerror = (e) => console.warn("[WS audio] error", e as any);

    ws.onmessage = (e) => {
      if (!(e.data instanceof ArrayBuffer)) return;
      const f32 = new Float32Array(e.data);
      // RMS for a quick level meter
      let sum = 0;
      for (let i = 0; i < f32.length; i++) sum += f32[i] * f32[i];
      const rms = Math.sqrt(sum / Math.max(1, f32.length));
      // Scale a bit so typical broadcast peaks are visible
      setAudioLevel(Math.max(0, Math.min(1, rms * 2)));
    };

    return () => { try { ws.close(); } catch {} };
  }, []);

  return (
    <RadioContext.Provider
      value={{
        prediction,
        confidence,
        activeTransition,

        fsmState,
        station,

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
}

