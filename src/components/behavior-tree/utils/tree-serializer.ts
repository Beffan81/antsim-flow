import { Node, Edge } from '@xyflow/react';
import { BehaviorTree } from '@/hooks/use-persisted-behavior-tree';

export interface FlowData {
  nodes: Node[];
  edges: Edge[];
}

// Convert behavior tree JSON to React Flow format
export function treeToFlow(tree: BehaviorTree): FlowData {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  
  let nodeCounter = 0;
  const getNodeId = () => `node-${nodeCounter++}`;

  function processNode(nodeData: any, parentId?: string, position = { x: 250, y: 50 }): string {
    const nodeId = getNodeId();
    
    let nodeType: string;
    let data: any = { label: nodeData.name || nodeData.type };
    
    // Determine node type and data based on JSON structure
    if (nodeData.type === 'selector') {
      nodeType = 'selector';
    } else if (nodeData.type === 'sequence') {
      nodeType = 'sequence';
    } else if (nodeData.type === 'condition') {
      nodeType = 'condition';
      data.condition = nodeData.condition;
    } else if (nodeData.type === 'step') {
      nodeType = 'action';
      data.step = nodeData.step;
    } else {
      nodeType = 'root';
    }

    const node: Node = {
      id: nodeId,
      type: nodeType,
      position,
      data,
    };
    
    nodes.push(node);
    
    // Create edge from parent if exists
    if (parentId) {
      edges.push({
        id: `edge-${parentId}-${nodeId}`,
        source: parentId,
        target: nodeId,
        type: 'behavior',
      });
    }
    
    // Process children
    if (nodeData.children && Array.isArray(nodeData.children)) {
      nodeData.children.forEach((child: any, index: number) => {
        const childPosition = {
          x: position.x + (index - (nodeData.children.length - 1) / 2) * 200,
          y: position.y + 150,
        };
        processNode(child, nodeId, childPosition);
      });
    }
    
    return nodeId;
  }
  
  // Start with root node
  if (tree.root) {
    processNode(tree.root);
  } else {
    // Create a default root node
    nodes.push({
      id: 'root-1',
      type: 'root',
      position: { x: 250, y: 50 },
      data: { label: 'Root' },
    });
  }
  
  return { nodes, edges };
}

// Convert React Flow format back to behavior tree JSON
export function flowToTree(nodes: Node[], edges: Edge[]): BehaviorTree | null {
  if (nodes.length === 0) return null;
  
  // Find root node
  const rootNode = nodes.find(node => node.type === 'root');
  if (!rootNode) return null;
  
  function buildTreeNode(nodeId: string): any {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return null;
    
    const children: any[] = [];
    
    // Find child nodes through edges
    const childEdges = edges.filter(edge => edge.source === nodeId);
    const childNodes = childEdges
      .map(edge => nodes.find(n => n.id === edge.target))
      .filter(Boolean)
      .sort((a, b) => (a!.position.x || 0) - (b!.position.x || 0)); // Sort by x position
    
    childNodes.forEach(childNode => {
      if (childNode) {
        const childTreeNode = buildTreeNode(childNode.id);
        if (childTreeNode) {
          children.push(childTreeNode);
        }
      }
    });
    
    // Build the tree node based on type
    const treeNode: any = {
      type: node.type === 'root' ? 'selector' : node.type, // Root becomes selector in JSON
      name: node.data.label || node.type,
    };
    
    if (node.type === 'condition' && node.data.condition) {
      treeNode.condition = node.data.condition;
    }
    
    if (node.type === 'action' && node.data.step) {
      treeNode.type = 'step';
      treeNode.step = node.data.step;
    }
    
    if (children.length > 0) {
      treeNode.children = children;
    }
    
    return treeNode;
  }
  
  const root = buildTreeNode(rootNode.id);
  return root ? { root } : null;
}