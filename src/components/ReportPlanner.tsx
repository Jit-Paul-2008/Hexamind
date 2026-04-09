"use client";

import React, { useState } from 'react';
import { TaxonomyNode } from '@/types';

interface ReportPlannerProps {
  query: string;
  initialTaxonomy: TaxonomyNode[];
  onConfirm: (taxonomy: TaxonomyNode[]) => void;
  onCancel: () => void;
}

const ROOT_ROLE_CYCLE = ['researcher', 'historian', 'auditor', 'analyst'];

const makeId = (prefix: string): string => `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;

const cloneNodes = (nodes: TaxonomyNode[]): TaxonomyNode[] =>
  nodes.map((node) => ({
    ...node,
    children: cloneNodes(node.children || []),
  }));

const flattenNodes = (nodes: TaxonomyNode[]): TaxonomyNode[] => {
  const items: TaxonomyNode[] = [];
  for (const node of nodes) {
    items.push({ ...node, children: cloneNodes(node.children || []) });
  }
  return items;
};

const normalizeOutline = (query: string, nodes: TaxonomyNode[]): TaxonomyNode[] => {
  const topic = query.trim().replace(/\s+/g, ' ');
  const cleaned = flattenNodes(nodes)
    .map((node) => ({
      ...node,
      topic: node.topic.trim(),
      children: cloneNodes(node.children || []),
    }))
    .filter((node) => node.topic.length > 0);

  const defaults: Array<{ topic: string; role: string }> = [
    { topic: `Scope and framing of ${topic}`, role: 'researcher' },
    { topic: `Current evidence and landscape for ${topic}`, role: 'researcher' },
    { topic: `Historical and policy context for ${topic}`, role: 'historian' },
    { topic: `Key dimensions, subtopics, and mechanisms in ${topic}`, role: 'researcher' },
    { topic: `Constraints, risks, and failure modes in ${topic}`, role: 'auditor' },
    { topic: `Regional or institutional differences in ${topic}`, role: 'historian' },
    { topic: `Implementation pathways and practical levers for ${topic}`, role: 'analyst' },
    { topic: `Metrics, benchmarks, and success criteria for ${topic}`, role: 'researcher' },
  ];

  const outline: TaxonomyNode[] = cleaned.slice(0, 10);
  for (const item of defaults) {
    if (outline.length >= 10) break;
    const alreadyPresent = outline.some((node) => node.topic.toLowerCase() === item.topic.toLowerCase());
    if (!alreadyPresent) {
      outline.push({
        id: makeId('section'),
        topic: item.topic,
        role: item.role,
        children: [],
      });
    }
  }

  while (outline.length < 6) {
    outline.push({
      id: makeId('section'),
      topic: `Additional angle on ${topic}`,
      role: ROOT_ROLE_CYCLE[outline.length % ROOT_ROLE_CYCLE.length],
      children: [],
    });
  }

  return outline.slice(0, 10).map((node, index) => ({
    ...node,
    role: node.role || ROOT_ROLE_CYCLE[index % ROOT_ROLE_CYCLE.length],
    children: cloneNodes(node.children || []),
  }));
};

export default function ReportPlanner({ query, initialTaxonomy, onConfirm, onCancel }: ReportPlannerProps) {
  const [taxonomy, setTaxonomy] = useState<TaxonomyNode[]>(() => normalizeOutline(query, initialTaxonomy));

  const updateNode = (id: string, updates: Partial<TaxonomyNode>) => {
    const mapNodes = (nodes: TaxonomyNode[]): TaxonomyNode[] => {
      return nodes.map(node => {
        if (node.id === id) {
          return { ...node, ...updates };
        }
        if (node.children) {
          return { ...node, children: mapNodes(node.children) };
        }
        return node;
      });
    };
    setTaxonomy(mapNodes(taxonomy));
  };

  const addRootSection = () => {
    const nextRole = ROOT_ROLE_CYCLE[taxonomy.length % ROOT_ROLE_CYCLE.length];
    setTaxonomy([
      ...taxonomy,
      {
        id: makeId('section'),
        topic: 'New report section',
        role: nextRole,
        children: [],
      },
    ]);
  };

  const addBranch = (parentId: string) => {
    const mapNodes = (nodes: TaxonomyNode[]): TaxonomyNode[] => {
      return nodes.map(node => {
        if (node.id === parentId) {
          const newId = makeId(node.id);
          return {
            ...node,
            children: [
              ...node.children,
              { id: newId, topic: 'New subtopic', role: 'researcher', children: [] }
            ]
          };
        }
        if (node.children) {
          return { ...node, children: mapNodes(node.children) };
        }
        return node;
      });
    };
    setTaxonomy(mapNodes(taxonomy));
  };

  const removeNode = (id: string) => {
    const filterNodes = (nodes: TaxonomyNode[]): TaxonomyNode[] => {
      return nodes
        .filter(node => node.id !== id)
        .map(node => ({
          ...node,
          children: node.children ? filterNodes(node.children) : []
        }));
    };
    setTaxonomy(filterNodes(taxonomy));
  };

  const confirmOutline = () => {
    onConfirm(normalizeOutline(query, taxonomy));
  };

  return (
    <div className="w-full max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
      <div className="glass-card overflow-hidden border-[#F2F2F7]">
        {/* Header */}
        <div className="bg-[#1D1D1F] px-8 py-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold tracking-tight">Report Outline Planner</h3>
              <p className="text-[11px] text-[#86868B] uppercase font-bold tracking-widest mt-1">Edit 6-10 report points and subpoints before synthesis</p>
            </div>
            <div className="flex items-center space-x-3">
              <button 
                onClick={onCancel}
                className="text-[12px] font-bold text-[#86868B] hover:text-white transition-colors uppercase tracking-wider"
              >
                Cancel
              </button>
              <button 
                onClick={confirmOutline}
                className="bg-white text-[#1D1D1F] text-[12px] font-black px-6 py-2 rounded-full hover:bg-[#F2F2F7] transition-all uppercase tracking-wider shadow-lg"
              >
                Begin Research
              </button>
            </div>
          </div>
          <p className="mt-4 text-[11px] text-[#B5B5B7] max-w-2xl">
            The outline is user-owned: edit section headings, add subtopics, or add new sections. Hidden internal roles are assigned only after you confirm.
          </p>
        </div>

        {/* Tree Editor Area */}
        <div className="p-8 bg-white/50 min-h-100">
          <div className="flex items-center justify-between mb-4">
            <div className="text-[11px] uppercase tracking-[0.24em] font-bold text-[#86868B]">
              {taxonomy.length} outline points
            </div>
            <button
              onClick={addRootSection}
              className="text-[11px] font-bold uppercase tracking-widest text-[#007AFF] hover:underline"
            >
              + Add Section
            </button>
          </div>
          <div className="space-y-6">
            {taxonomy.map((node) => (
              <NodeEditor 
                key={node.id} 
                node={node} 
                level={0}
                onUpdate={(updates) => updateNode(node.id, updates)}
                onAddBranch={() => addBranch(node.id)}
                onRemove={() => removeNode(node.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

interface NodeEditorProps {
  node: TaxonomyNode;
  level: number;
  onUpdate: (updates: Partial<TaxonomyNode>) => void;
  onAddBranch: () => void;
  onRemove: () => void;
}

function NodeEditor({ node, level, onUpdate, onAddBranch, onRemove }: NodeEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [tempTopic, setTempTopic] = useState(node.topic);

  return (
    <div className={`relative ${level > 0 ? 'ml-10 mt-4' : ''}`}>
      {/* Visual Connector for children */}
      {level > 0 && (
        <div className="absolute -left-6 top-5 w-6 h-px bg-[#E5E5E7]"></div>
      )}
      {level > 0 && (
        <div className="absolute -left-6 -top-10 bottom-5 w-px bg-[#E5E5E7]"></div>
      )}

      <div className="group flex items-start space-x-4">
        <div className="mt-1">
          <div className="appearance-none text-[9px] font-black uppercase tracking-tighter px-2 py-1 rounded border border-[#E5E5E7] bg-[#F7F7F8] text-[#86868B]">
            {level === 0 ? 'Section' : 'Subtopic'}
          </div>
        </div>

        {/* Topic Content */}
        <div className="flex-1">
          {isEditing ? (
            <input 
              autoFocus
              placeholder="Edit section title"
              className="w-full text-sm font-semibold text-[#1D1D1F] border-b border-[#007AFF] bg-transparent outline-none pb-1"
              value={tempTopic}
              onChange={(e) => setTempTopic(e.target.value)}
              onBlur={() => {
                onUpdate({ topic: tempTopic });
                setIsEditing(false);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  onUpdate({ topic: tempTopic });
                  setIsEditing(false);
                }
              }}
            />
          ) : (
            <span 
              onClick={() => setIsEditing(true)}
              className="text-sm font-semibold text-[#1D1D1F] cursor-text hover:text-[#007AFF] transition-colors"
            >
              {node.topic}
            </span>
          )}

          {/* Inline Actions (visible on hover) */}
          <div className="flex items-center space-x-4 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button 
              onClick={onAddBranch}
              className="text-[9px] font-bold text-[#007AFF] hover:underline uppercase tracking-widest"
            >
              + Subtopic
            </button>
            <button 
              onClick={onRemove}
              className="text-[9px] font-bold text-[#FF3B30] hover:underline uppercase tracking-widest"
            >
              Remove
            </button>
          </div>
        </div>
      </div>

      {/* Children */}
      {node.children && node.children.length > 0 && (
        <div className="mt-2">
          {node.children.map((child) => (
            <NodeEditor 
              key={child.id} 
              node={child} 
              level={level + 1}
              onUpdate={(updates) => {
                const newChildren = node.children.map(c => c.id === child.id ? { ...c, ...updates } : c);
                onUpdate({ children: newChildren });
              }}
              onAddBranch={() => {
                const newId = `${child.id}_${Date.now().toString().slice(-4)}`;
                const newChildren = node.children.map(c => 
                  c.id === child.id ? { 
                    ...c, 
                    children: [...c.children, { id: newId, topic: 'New Sub-topic', role: 'researcher', children: [] }] 
                  } : c
                );
                onUpdate({ children: newChildren });
              }}
              onRemove={() => {
                const newChildren = node.children.filter(c => c.id !== child.id);
                onUpdate({ children: newChildren });
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
