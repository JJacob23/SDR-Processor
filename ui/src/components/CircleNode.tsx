import { Handle, Position } from "reactflow";

export default function CircleNode({ data }: any) {
  const active = data.active ?? false;

  return (
    <div
      style={{
        width: 100,
        height: 100,
        borderRadius: "50%",
        background: active ? "#00ff00" : "#222",
        border: active ? "3px solid #00ff00" : "1px solid #444",
        color: active ? "black" : "#aaa",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: "bold",
        textAlign: "center",
        position: "relative",
        fontSize: 18,
        lineHeight: 1.2,
      }}
    >
      {data.label}

      {/* Give each side its own ID */}
      <Handle type="source" id="top" position={Position.Top} style={{ background: "transparent" }} />
      <Handle type="source" id="right" position={Position.Right} style={{ background: "transparent" }} />
      <Handle type="source" id="bottom" position={Position.Bottom} style={{ background: "transparent" }} />
      <Handle type="source" id="left" position={Position.Left} style={{ background: "transparent" }} />

      <Handle type="target" id="t-top" position={Position.Top} style={{ background: "transparent" }} />
      <Handle type="target" id="t-right" position={Position.Right} style={{ background: "transparent" }} />
      <Handle type="target" id="t-bottom" position={Position.Bottom} style={{ background: "transparent" }} />
      <Handle type="target" id="t-left" position={Position.Left} style={{ background: "transparent" }} />
    </div>
  );
}
