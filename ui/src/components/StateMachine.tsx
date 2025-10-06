import React, { useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  MarkerType,
  ReactFlowProvider,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";
import CircleNode from "./CircleNode";
import { useRadio } from "../context/RadioContext";  // 👈 import the shared context

/* ──────────────────────────────
   Inner graph wrapper (auto-fit)
──────────────────────────────── */
function FlowInner({ nodes, edges, nodeTypes }: any) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    fitView({ padding: 0.1, duration: 800 });
    const onResize = () => fitView({ padding: 0.1, duration: 800 });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [fitView]);

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView>
      <Controls />
      <Background color="#333" gap={12} />
    </ReactFlow>
  );
}

/* ──────────────────────────────
   Main FSM component
──────────────────────────────── */
export default function StateMachine() {
  // pull live state from provider instead of simulating
  const { activeNode, activeEdge } = useRadio();

  /* --- Label + edge styling --- */
  const labelStyle = {
    fill: "#ccc",
    fontSize: 14,
    fontWeight: 600,
  };
  const labelBgStyle = { fill: "#222", stroke: "#444" };

  const baseEdgeStyle = {
    stroke: "#555",
    strokeWidth: 2.5,
  };
  const markerDark: any = {
    type: MarkerType.ArrowClosed,
    color: "#555",
    width: 26,
    height: 26,
  };

  /* --- Node setup --- */
  const labels: Record<string, string> = {
    primary: "Primary Station",
    patience1: "Patience 1",
    patience2: "Patience 2",
    secondary: "Secondary Station",
  };

  const nodesInit: Node[] = [
    { id: "primary", type: "circle", data: { label: labels.primary }, position: { x: 100, y: 150 } },
    { id: "patience1", type: "circle", data: { label: labels.patience1 }, position: { x: 250, y: 0 } },
    { id: "secondary", type: "circle", data: { label: labels.secondary }, position: { x: 400, y: 150 } },
    { id: "patience2", type: "circle", data: { label: labels.patience2 }, position: { x: 250, y: 300 } },
  ];

  /* --- All edges --- */
  const edgesInit: Edge[] = [
    { id: "ad1", source: "primary", sourceHandle: "right", target: "patience1", targetHandle: "t-bottom",  label: "Ad" },
    { id: "ad2", source: "patience1", sourceHandle: "right", target: "secondary",  label: "Ad" },
    { id: "ad3", source: "secondary", sourceHandle: "left", target: "patience2", targetHandle: "t-top",  label: "Ad" },
    { id: "ad4", source: "patience2", sourceHandle: "left", target: "primary", targetHandle: "t-bottom",  label: "Ad" },
    { id: "song1", source: "patience1", sourceHandle: "left", target: "primary", targetHandle: "t-top",  label: "Song" },
    { id: "song2", source: "patience2", sourceHandle: "right", target: "secondary", targetHandle: "t-bottom",  label: "Song" },
    { id: "song_stay1", source: "primary", sourceHandle: "top", target: "primary", targetHandle: "t-bottom",  label: "Song" },
    { id: "song_stay2", source: "secondary", sourceHandle: "top", target: "secondary", targetHandle: "t-bottom",  label: "Song" },
  ];

  /* --- Apply highlights from provider state --- */
  const nodes = nodesInit.map((n) => ({
    ...n,
    data: { ...n.data, active: n.id === activeNode },
  }));

  const edges = edgesInit.map((e) => {
    const isActive = e.id === activeEdge;
    return {
      ...e,
      style: isActive
        ? { stroke: "#00ff00", strokeWidth: 3.5 }
        : baseEdgeStyle,
      markerEnd: {
        ...markerDark,
        color: isActive ? "#00ff00" : markerDark.color,
      },
      labelStyle: { ...labelStyle, fill: isActive ? "#00ff00" : "#ccc" },
      labelBgStyle: { ...labelBgStyle, fill: isActive ? "#003300" : "#222" },
      labelBgPadding: [4, 2],
      labelBgBorderRadius: 3,
    };
  });

  const nodeTypes = { circle: CircleNode };

  return (
    <div className="flex justify-center items-center w-full h-full">
      <div className="w-full h-full bg-black/40 border border-gray-700 rounded-lg overflow-hidden">
        <ReactFlowProvider>
          <FlowInner nodes={nodes} edges={edges} nodeTypes={nodeTypes} />
        </ReactFlowProvider>
      </div>
    </div>
  );
}
