import React, { useEffect, useState } from "react";
import ReactFlow, { MiniMap, Controls, Background } from "reactflow";
import "reactflow/dist/style.css";


type FlowNode = { id: string; data: { label: string }; position: { x: number; y: number } };
const nodesInit: FlowNode[] = [ 
  { id: "primary", data: { label: "Primary" }, position: { x: 0, y: 0 } },
  { id: "patience1", data: { label: "Patience 1" }, position: { x: 200, y: 100 } },
  { id: "patience2", data: { label: "Patience 2" }, position: { x: 400, y: 0 } },
  { id: "secondary", data: { label: "Secondary" }, position: { x: 600, y: 100 } },
];

const edges = [
  { id: "e1", source: "primary", target: "patience1" },
  { id: "e2", source: "patience1", target: "patience2" },
  { id: "e3", source: "patience2", target: "secondary" },
  { id: "e4", source: "secondary", target: "primary" },
];

export default function StateMachineGraph() {
  const [active, setActive] = useState("primary");

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/state");
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      setActive(msg.state);
    };
    return () => ws.close();
  }, []);

  const nodes = nodesInit.map((n) => ({
    ...n,
    style: {
      background: n.id === active ? "#00ff00" : "#444",
      color: "black",
      borderRadius: "8px",
      padding: "8px",
    },
  }));

  return (
    <div className="h-[400px] w-[400px]">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <MiniMap />
        <Controls />
        <Background />
      </ReactFlow>
    </div>
  );
}

