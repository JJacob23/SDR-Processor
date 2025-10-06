import React from "react";
import AudioVisualizer from "./components/AudioVisualizer";
import StateMachineGraph from "./components/StateMachineGraph";
import StatusBar from "./components/StatusBar";

export default function App() {
  return (
    <div className="h-screen flex flex-col">
      <div className="flex flex-1">
        <div className="w-1/2 p-2 border-r border-gray-700">
          <AudioVisualizer />
        </div>
        <div className="w-[500px] p-2 h-[500px]">
          <StateMachineGraph />
        </div>
      </div>
      <StatusBar />
    </div>
  );
}

