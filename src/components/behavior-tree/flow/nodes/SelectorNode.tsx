import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { MoreHorizontal } from 'lucide-react';

interface SelectorNodeData {
  label: string;
}

const SelectorNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as { label?: string };
  return (
    <div className={`
      px-4 py-3 rounded-lg border-2 bg-gradient-to-br from-orange-500/10 to-orange-500/5 
      ${selected ? 'border-orange-500 shadow-lg' : 'border-border'}
      transition-all duration-200 min-w-[120px]
    `}>
      <Handle 
        type="target" 
        position={Position.Top} 
        className="w-3 h-3 bg-orange-500 border-2 border-background"
      />
      
      <div className="flex items-center gap-2 justify-center">
        <MoreHorizontal className="w-4 h-4 text-orange-600" />
        <span className="font-medium text-sm text-foreground">
          {nodeData.label || 'Selector'}
        </span>
      </div>
      
      <Handle 
        type="source" 
        position={Position.Bottom} 
        className="w-3 h-3 bg-orange-500 border-2 border-background"
      />
    </div>
  );
});

SelectorNode.displayName = 'SelectorNode';

export { SelectorNode };