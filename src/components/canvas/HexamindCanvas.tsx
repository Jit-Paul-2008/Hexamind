"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import InputNode from "./InputNode";
import AgentNode from "./AgentNode";
import OutputNode from "./OutputNode";
import AnimatedEdge from "./AnimatedEdge";
import { INITIAL_NODES } from "@/lib/nodes";
import { INITIAL_EDGES } from "@/lib/edges";

export default function HexamindCanvas() {
  const nodeTypes = useMemo(
    () => ({
      inputNode: InputNode,
      agentNode: AgentNode,
      outputNode: OutputNode,
    }),
    []
  );

  const edgeTypes = useMemo(
    () => ({
      animatedEdge: AnimatedEdge,
    }),
    []
  );

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={INITIAL_NODES}
        edges={INITIAL_EDGES}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag
        zoomOnScroll
        zoomOnPinch
        minZoom={0.4}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
        colorMode="dark"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={28}
          size={1}
          color="rgba(182,186,197,0.06)"
        />
        <Controls
          showInteractive={false}
          className="!bg-white/5 !border-white/10 !rounded-xl !backdrop-blur-xl [&>button]:!bg-transparent [&>button]:!border-white/10 [&>button]:!text-white/40 [&>button:hover]:!bg-white/10 [&>button:hover]:!text-white/70"
        />
      </ReactFlow>
    </div>
  );
}
