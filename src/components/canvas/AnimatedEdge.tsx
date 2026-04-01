"use client";

import { BaseEdge, type EdgeProps, getBezierPath } from "@xyflow/react";
import { usePipelineStore } from "@/lib/store";

export default function AnimatedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps) {
  const color = (data as Record<string, unknown>)?.color as string || "#525a6e";

  // Determine if the source or target node is active/done to animate this edge
  const sourceId = id.split("-")[0];
  const sourceStatus = usePipelineStore(
    (s) => s.nodeStatuses[sourceId] || "idle"
  );
  const isActive = sourceStatus === "done" || sourceStatus === "active";

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <>
      {/* Base edge — always visible, dim when idle */}
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          stroke: isActive ? color : "#1e2028",
          strokeWidth: isActive ? 2 : 1,
          strokeDasharray: isActive ? "none" : "6 4",
          transition: "stroke 0.6s, stroke-width 0.6s",
          opacity: isActive ? 0.8 : 0.3,
        }}
      />
      {/* Animated particle dot — only when active */}
      {isActive && (
        <>
          <circle r="3" fill={color} filter={`drop-shadow(0 0 4px ${color})`}>
            <animateMotion
              dur="1.8s"
              repeatCount="indefinite"
              path={edgePath}
            />
          </circle>
          <circle r="1.5" fill="#fff" opacity="0.7">
            <animateMotion
              dur="1.8s"
              repeatCount="indefinite"
              path={edgePath}
            />
          </circle>
        </>
      )}
    </>
  );
}
