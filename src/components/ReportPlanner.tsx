"use client";

import React, { useState } from 'react';
import { TaxonomyNode } from '@/types';

interface ReportPlannerProps {
  initialTaxonomy: TaxonomyNode[];
  onConfirm: (taxonomy: TaxonomyNode[]) => void;
  onCancel: () => void;
}

const ROLES = ['researcher', 'historian', 'auditor', 'analyst'];

export default function ReportPlanner({ initialTaxonomy, onConfirm, onCancel }: ReportPlannerProps) {
  const [taxonomy, setTaxonomy] = useState<TaxonomyNode[]>(initialTaxonomy);

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

  const addBranch = (parentId: string) => {
    const mapNodes = (nodes: TaxonomyNode[]): TaxonomyNode[] => {
      return nodes.map(node => {
        if (node.id === parentId) {
          const newId = `${node.id}_${Date.now().toString().slice(-4)}`;
          return {
            ...node,
            children: [
              ...node.children,
              { id: newId, topic: 'New Sub-topic', role: 'researcher', children: [] }
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

  return (
    <div className="w-full max-w-4xl mx-auto animate-in fade-in zoom-in-95 duration-500">
      <div className="glass-card overflow-hidden border-[#F2F2F7]">
        {/* Header */}
        <div className="bg-[#1D1D1F] px-8 py-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold tracking-tight">Strategic Taxonomy Planner</h3>
              <p className="text-[11px] text-[#86868B] uppercase font-bold tracking-widest mt-1">Review and refine the research roadmap</p>
            </div>
            <div className="flex items-center space-x-3">
              <button 
                onClick={onCancel}
                className="text-[12px] font-bold text-[#86868B] hover:text-white transition-colors uppercase tracking-wider"
              >
                Cancel
              </button>
              <button 
                onClick={() => onConfirm(taxonomy)}
                className="bg-white text-[#1D1D1F] text-[12px] font-black px-6 py-2 rounded-full hover:bg-[#F2F2F7] transition-all uppercase tracking-wider shadow-lg"
              >
                Begin Research
              </button>
            </div>
          </div>
        </div>

        {/* Tree Editor Area */}
        <div className="p-8 bg-white/50 min-h-[400px]">
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
        <div className="absolute -left-6 top-5 w-6 h-[1px] bg-[#E5E5E7]"></div>
      )}
      {level > 0 && (
        <div className="absolute -left-6 -top-10 bottom-5 w-[1px] bg-[#E5E5E7]"></div>
      )}

      <div className="group flex items-start space-x-4">
        {/* Role Badge */}
        <div className="mt-1">
          <select 
            value={node.role}
            onChange={(e) => onUpdate({ role: e.target.value })}
            className={`
              appearance-none text-[9px] font-black uppercase tracking-tighter px-2 py-1 rounded cursor-pointer border transition-all
              ${node.role === 'researcher' ? 'bg-[#EBF5FF] text-[#007AFF] border-[#007AFF]/20' : ''}
              ${node.role === 'historian' ? 'bg-[#F5EBFF] text-[#AF52DE] border-[#AF52DE]/20' : ''}
              ${node.role === 'auditor' ? 'bg-[#FFF2F2] text-[#FF3B30] border-[#FF3B30]/20' : ''}
              ${node.role === 'analyst' ? 'bg-[#E8F8F0] text-[#34C759] border-[#34C759]/20' : ''}
            `}
          >
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        {/* Topic Content */}
        <div className="flex-1">
          {isEditing ? (
            <input 
              autoFocus
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
              + Branch
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
