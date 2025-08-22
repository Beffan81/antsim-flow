import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  NodeTypes,
  EdgeTypes,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { RootNode } from './nodes/RootNode';
import { SelectorNode } from './nodes/SelectorNode';
import { SequenceNode } from './nodes/SequenceNode';
import { ConditionNode } from './nodes/ConditionNode';
import { ActionNode } from './nodes/ActionNode';
import { BehaviorEdge } from './edges/BehaviorEdge';

import { BehaviorTree } from '@/hooks/use-persisted-behavior-tree';
import { treeToFlow, flowToTree } from '../utils/tree-serializer';

const nodeTypes: NodeTypes = {
  root: RootNode,
  selector: SelectorNode,
  sequence: SequenceNode,
  condition: ConditionNode,
  action: ActionNode,
};

const edgeTypes: EdgeTypes = {
  behavior: BehaviorEdge,
};

interface BehaviorTreeFlowProps {
  tree: BehaviorTree;
  onChange: (tree: BehaviorTree) => void;
  selectedNodeId?: string | null;
  onNodeSelect?: (nodeId: string | null) => void;
}

let id = 0;
const getId = () => `dndnode_${id++}`;

export const BehaviorTreeFlow = ({
  tree,
  onChange,
  selectedNodeId,
  onNodeSelect,
}: BehaviorTreeFlowProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Convert tree to flow format when tree changes
  useEffect(() => {
    const flowData = treeToFlow(tree);
    setNodes(flowData.nodes);
    setEdges(flowData.edges);
  }, [tree, setNodes, setEdges]);

  // Convert flow back to tree when nodes/edges change
  const handleFlowChange = useCallback(() => {
    const newTree = flowToTree(nodes, edges);
    if (newTree) {
      onChange(newTree);
    }
  }, [nodes, edges, onChange]);

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: 'behavior' }, eds)),
    [setEdges],
  );

  const handleNodesChange: OnNodesChange = useCallback((changes) => {
    onNodesChange(changes);
    setTimeout(handleFlowChange, 0); // Defer to next tick
  }, [onNodesChange, handleFlowChange]);

  const handleEdgesChange: OnEdgesChange = useCallback((changes) => {
    onEdgesChange(changes);
    setTimeout(handleFlowChange, 0); // Defer to next tick
  }, [onEdgesChange, handleFlowChange]);

  const handleNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    onNodeSelect?.(node.id);
  }, [onNodeSelect]);

  const handlePaneClick = useCallback(() => {
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = (event.target as Element).getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');
      const stepName = event.dataTransfer.getData('step-name');

      if (typeof type === 'undefined' || !type) {
        return;
      }

      const position = {
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      };

      const newNode: Node = {
        id: getId(),
        type,
        position,
        data: { 
          label: type.charAt(0).toUpperCase() + type.slice(1),
          ...(type === 'action' && stepName && {
            step: { name: stepName, params: {} }
          })
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes],
  );

  // Update selected state on nodes
  const nodesWithSelection = useMemo(() => 
    nodes.map(node => ({
      ...node,
      selected: node.id === selectedNodeId,
    })),
    [nodes, selectedNodeId]
  );

  return (
    <div className="w-full h-full bg-background">
      <ReactFlow
        nodes={nodesWithSelection}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: 'behavior',
        }}
      >
        <Background className="bg-muted/20" />
        <Controls className="bg-background border border-border shadow-sm" />
        <MiniMap 
          className="bg-background border border-border shadow-sm" 
          pannable 
          zoomable 
        />
      </ReactFlow>
    </div>
  );
};