import { useMemo } from "react";
import { useRadio } from "../context/RadioContext";
import { Volume2, VolumeX } from "lucide-react";

export default function StatusBar() {
  const {
    prediction,
    confidence,
    activeNode,
    audioLevel,
    isMuted,
    setIsMuted,
  } = useRadio();

  // Your WS gives frequency as numeric string in Hz
  const rawStation =
    (useRadio() as any)?.station ??
    (useRadio() as any)?.frequency ??
    activeNode ??
    null;

  const stationLabel = useMemo(() => {
    const mhz = toMHzFromHz(rawStation, 3);
    return mhz ?? (rawStation != null ? String(rawStation) : "—");
  }, [rawStation]);

  const confPct =
    typeof confidence === "number" && Number.isFinite(confidence)
      ? `${(confidence * 100).toFixed(1)}%`
      : "—";

  const levelPct = Math.max(0, Math.min(1, Number(audioLevel) || 0)) * 100;

  return (
    // 3 equal columns, anchored; bottom-aligned so nothing jumps vertically
    <div className="w-full bg-gray-900/70 border border-gray-700 rounded-xl px-4 py-2 text-sm grid grid-cols-3 items-end gap-4">
      {/* Left column: Station (anchored left) */}
      <div className="justify-self-start self-end flex items-baseline gap-2 min-w-0">
        <span className="text-gray-400">Station:</span>
        <span className="font-mono text-gray-100 whitespace-nowrap">{stationLabel}</span>
      </div>

      {/* Middle column: Prediction | Confidence laid out to opposite sides */}
      <div className="self-end grid grid-cols-2 items-baseline gap-x-6 min-w-0">
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="text-gray-400">Prediction: </span>
          <span className="font-mono text-gray-100 whitespace-nowrap truncate min-w-[12ch] max-w-[24ch]">
            {prediction ?? "—"}
          </span>
        </div>
        <div className="flex items-baseline gap-2 justify-self-end">
          <span className="text-gray-400">Conf:</span>
          <span className="font-mono text-gray-100 tabular-nums whitespace-nowrap min-w-[6ch] text-right">
            {confPct}
          </span>
        </div>
      </div>

      {/* Right column: Level + Mute (anchored right) */}
      <div className="justify-self-end self-end flex items-center gap-3">
        <div className="w-24 h-2 bg-gray-800 rounded overflow-hidden">
          <div
            className="h-full bg-emerald-400 transition-[width] duration-150"
            style={{ width: `${levelPct}%` }}
          />
        </div>

        <button
          onClick={() => setIsMuted((m: boolean) => !m)}
          className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-md border ${
            isMuted
              ? "border-gray-700 bg-gray-800 text-gray-200"
              : "border-emerald-700/40 bg-emerald-900/20 text-emerald-200"
          }`}
          title={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? (
            <>
              <VolumeX size={18} />
              <span>Muted</span>
            </>
          ) : (
            <>
              <Volume2 size={18} />
              <span>Unmuted</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

/** Fast path when the WS gives you a numeric (or numeric string) in Hz */
function toMHzFromHz(value: unknown, digits = 3): string | null {
  const num =
    typeof value === "string"
      ? Number(value.replace(/,/g, ""))
      : typeof value === "number"
      ? value
      : NaN;
  if (!Number.isFinite(num)) return null;
  const mhz = num / 1_000_000; // Hz -> MHz
  return trimZeros(mhz, digits) + " MHz";
}

/** 101.100 -> "101.1", 101.000 -> "101" */
function trimZeros(n: number, digits = 3): string {
  const s = n.toFixed(digits);
  return s.replace(/\.?0+$/, "");
}

