import React from "react";
import StatusBar from "./components/StatusBar";
import AudioVisualizer from "./components/AudioVisualizer";
import StateMachine from "./components/StateMachine";
import { RadioProvider } from "./context/RadioContext";

export default function App() {
  return (
    <RadioProvider>
      <div className="flex flex-col items-center justify-center min-h-screen w-screen bg-background text-gray-100">
        {/* ─────── Main Card ─────── */}
        <div className="flex flex-col w-[90vw] max-w-6xl h-[80vh] border border-gray-700 rounded-2xl shadow-xl overflow-hidden bg-black/70">
        <div className="text-3xl font-bold mb-04 tracking-wide text-green-400 border-b border-gray-700">
          SDR Processor Dashboard
        </div>
          {/* Two-column content */}
          <div className="flex flex-1">
            {/* Left: Audio visualizer */}
            <div className="w-1/2 border-r border-gray-700 p-4 flex flex-col">
              <h2 className="mb-2 text-xl text-center text-gray-200 font-semibold">
                Audio Visualizer
              </h2>
              <div className="flex-1 flex items-center justify-center">
                <AudioVisualizer />
              </div>
            </div>

            {/* Right: FSM graph */}
            <div className="w-1/2 p-4 flex flex-col">
              <h2 className="mb-2 text-xl text-center text-gray-200 font-semibold">
                State Machine
              </h2>
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <StateMachine />
              </div>
            </div>
          </div>

          {/* Bottom status bar */}
          <StatusBar />
        </div>
      </div>
    </RadioProvider>
  );
}
