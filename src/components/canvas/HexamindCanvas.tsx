"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import InputNode from "./InputNode";
import AgentNode from "./AgentNode";
import OutputNode from "./OutputNode";
import ProcessingNode from "./ProcessingNode";
import AnimatedEdge from "./AnimatedEdge";
import { INITIAL_NODES } from "@/lib/nodes";
import { INITIAL_EDGES } from "@/lib/edges";

export default function HexamindCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, , onEdgesChange] = useEdgesState(INITIAL_EDGES);

  const nodeTypes = useMemo(
    () => ({
      inputNode: InputNode,
      agentNode: AgentNode,
      outputNode: OutputNode,
      processingNode: ProcessingNode,
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
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={(_, draggedNode) => {
          setNodes((currentNodes) =>
            resolveOverlapForDraggedNode(currentNodes, draggedNode.id)
          );
        }}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
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

type NodeRect = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};

function resolveOverlapForDraggedNode(nodes: Node[], draggedId: string): Node[] {
  const index = nodes.findIndex((node) => node.id === draggedId);
  if (index === -1) {
    return nodes;
  }

  const updated = [...nodes];
  const dragged = { ...updated[index], position: { ...updated[index].position } };
  const step = 28;
  const maxPasses = 200;

  let pass = 0;
  while (pass < maxPasses) {
    const collidedWith = updated.find((node) => {
      if (node.id === dragged.id) {
        return false;
      }
      return isOverlapping(nodeRect(dragged), nodeRect(node), 16);
    });

    if (!collidedWith) {
      break;
    }

    dragged.position.x += step;
    if (dragged.position.x > 1400) {
      dragged.position.x = 40;
      dragged.position.y += step;
    }
    if (dragged.position.y > 1200) {
      dragged.position.y = 40;
    }
    pass += 1;
  }

  updated[index] = dragged;
  return updated;
}

function isOverlapping(a: NodeRect, b: NodeRect, gap: number): boolean {
  return !(
    a.right + gap <= b.left ||
    a.left >= b.right + gap ||
    a.bottom + gap <= b.top ||
    a.top >= b.bottom + gap
  );
}

function nodeRect(node: Node): NodeRect {
  const { width, height } = nodeSize(node.type);
  return {
    left: node.position.x,
    top: node.position.y,
    right: node.position.x + width,
    bottom: node.position.y + height,
  };
}

function nodeSize(type?: string): { width: number; height: number } {
  switch (type) {
    case "inputNode":
      return { width: 240, height: 120 };
    case "agentNode":
      return { width: 260, height: 180 };
    case "processingNode":
      return { width: 270, height: 190 };
    case "outputNode":
      return { width: 780, height: 1123 };
    default:
      return { width: 260, height: 180 };
  }
}
