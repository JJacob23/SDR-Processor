import { useEffect, useMemo } from "react";
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
import { useRadio } from "../context/RadioContext";

/* Auto-fit wrapper */
function FlowInner({ nodes, edges, nodeTypes }: any) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    fitView({ padding: 0.1, duration: 600 });
    const onResize = () => fitView({ padding: 0.1, duration: 600 });
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

export default function StateMachine() {
  const { fsmState, activeTransition } = useRadio() as any;

  /* Styling */
  const labelStyle = { fill: "#ccc", fontSize: 14, fontWeight: 600 };
  const labelBgStyle = { fill: "#222", stroke: "#444" };
  const baseEdgeStyle = { stroke: "#555", strokeWidth: 2.5 };
  const markerDark: any = { type: MarkerType.ArrowClosed, color: "#555", width: 26, height: 26 };

  /* Nodes */
  const nodesInit: Node[] = [
    { id: "primary",   type: "circle", data: { label: "Primary Station" },   position: { x: 100, y: 150 } },
    { id: "patience1", type: "circle", data: { label: "Patience 1" },        position: { x: 250, y:   0 } },
    { id: "secondary", type: "circle", data: { label: "Secondary Station" }, position: { x: 400, y: 150 } },
    { id: "patience2", type: "circle", data: { label: "Patience 2" },        position: { x: 250, y: 300 } },
  ];

  /* Edges */
  const edgesInit: Edge[] = [
    { id: "ad1",        source: "primary",   sourceHandle: "right", target: "patience1", targetHandle: "t-bottom", label: "Ad" },
    { id: "ad2",        source: "patience1", sourceHandle: "right", target: "secondary",                                         label: "Ad" },
    { id: "ad3",        source: "secondary", sourceHandle: "left",  target: "patience2", targetHandle: "t-top",   label: "Ad" },
    { id: "ad4",        source: "patience2", sourceHandle: "left",  target: "primary",   targetHandle: "t-bottom", label: "Ad" },
    { id: "song1",      source: "patience1", sourceHandle: "left",  target: "primary",   targetHandle: "t-top",   label: "Song" },
    { id: "song2",      source: "patience2", sourceHandle: "right", target: "secondary", targetHandle: "t-bottom",label: "Song" },
    { id: "song_stay1", source: "primary",   sourceHandle: "top",   target: "primary",   targetHandle: "t-bottom",label: "Song" },
    { id: "song_stay2", source: "secondary", sourceHandle: "top",   target: "secondary", targetHandle: "t-bottom",label: "Song" },
  ];

  /**
   * Highlight the *incoming* edge for the current state, chosen by label.
   * Mapping is expressed by TARGET state (the node we are in now).
   * Note: for 'song' into primary/secondary there are two possibilities
   * (stay vs. from patience). We default to the "stay" edge.
   */
  const incomingMap: Record<string, Record<string, string | null>> = {
    primary:   { ad: "ad4",   song: "song_stay1" }, // from patience2 (ad) or stay on song
    patience1: { ad: "ad1",   song: null },         // only ad goes into patience1
    secondary: { ad: "ad2",   song: "song_stay2" }, // from patience1 (ad) or stay on song
    patience2: { ad: "ad3",   song: null },         // only ad goes into patience2
  };

  /* Compute the one active (incoming) edge id */
  const activeEdgeId = useMemo(() => {
    const stateKey = (fsmState || "").toLowerCase();
    const labelKey = (activeTransition || "").toLowerCase();
    return incomingMap[stateKey]?.[labelKey] ?? null;
  }, [fsmState, activeTransition]);

  /* Highlighted node (current FSM state) */
  const nodes = useMemo(
    () => nodesInit.map((n) => ({ ...n, data: { ...n.data, active: !!fsmState && n.id === fsmState } })),
    [fsmState]
  );

  const edges = useMemo(
    () =>
      edgesInit.map((e) => {
        const isActive = !!activeEdgeId && e.id === activeEdgeId;
        return {
          ...e,
          style: isActive ? { stroke: "#00ff00", strokeWidth: 3.5 } : baseEdgeStyle,
          markerEnd: { ...markerDark, color: isActive ? "#00ff00" : markerDark.color },
          labelStyle: { ...labelStyle, fill: isActive ? "#00ff00" : "#ccc" },
          labelBgStyle: { ...labelBgStyle, fill: isActive ? "#003300" : "#222" },
          labelBgPadding: [4, 2],
          labelBgBorderRadius: 3,
        };
      }),
    [activeEdgeId]
  );

  const nodeTypes = useMemo(() => ({ circle: CircleNode }), []);

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

