import { useEffect, useRef, useState } from "react";
import { useRadio } from "../context/RadioContext";
import { Volume2, VolumeX } from "lucide-react";

/**
 * StatusBar — displays classifier state, confidence, audio lag, and mute toggle.
 */
export default function StatusBar() {
  const {
    prediction,
    confidence,
    activeNode,
    audioLevel,
    isMuted,
    setIsMuted,
  } = useRadio();

  const [lag, setLag] = useState<number>(0);
  const lastTimeRef = useRef<number>(performance.now());

  // Measure time between audio level updates to estimate lag
  useEffect(() => {
    const now = performance.now();
    const diff = now - lastTimeRef.current;
    lastTimeRef.current = now;

    // Smooth rolling average to reduce jitter
    setLag((prev: number) => prev * 0.8 + diff * 0.2);
  }, [audioLevel]);

  return (
    <div className="flex justify-between items-center px-6 py-3 border-t border-gray-700 text-lg text-gray-200 bg-black/60 font-medium">
      {/* Left: Station */}
      <div>
        Station:&nbsp;
        <span className="text-green-400">{activeNode ?? "--"}</span>
      </div>

      {/* Center: Last prediction */}
      <div>
        Last Prediction:&nbsp;
        <span className="text-green-400">{prediction ?? "--"}</span>
        {confidence !== null && (
          <span className="text-gray-400 ml-1">
            ({(confidence * 100).toFixed(1)}%)
          </span>
        )}
      </div>

      {/* Right: Lag + Mute */}
      <div className="flex items-center gap-4">
        <div>
          Lag:&nbsp;
          <span className="text-green-400">
            {lag ? lag.toFixed(1) : "--"} ms
          </span>
        </div>

        <button
          onClick={() => setIsMuted((prev: boolean) => !prev)}
          className={`ml-2 w-28 px-3 py-1 border border-gray-600 rounded-md hover:bg-gray-800 transition flex items-center justify-center gap-2 ${
            isMuted ? "text-red-400" : "text-green-400"
          }`}
        >
          {isMuted ? (
            <>
              <VolumeX size={18} /> <span>Muted</span>
            </>
          ) : (
            <>
              <Volume2 size={18} /> <span>Unmuted</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

