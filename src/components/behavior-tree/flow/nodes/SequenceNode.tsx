import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { ArrowRight } from 'lucide-react';

interface SequenceNodeData {
  label: string;
}

const SequenceNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as { label?: string };
  return (
    <div className={`
      px-4 py-3 rounded-lg border-2 bg-gradient-to-br from-blue-500/10 to-blue-500/5 
      ${selected ? 'border-blue-500 shadow-lg' : 'border-border'}
      transition-all duration-200 min-w-[120px]
    `}>
      <Handle 
        type="target" 
        position={Position.Top} 
        className="w-3 h-3 bg-blue-500 border-2 border-background"
      />
      
      <div className="flex items-center gap-2 justify-center">
        <ArrowRight className="w-4 h-4 text-blue-600" />
        <span className="font-medium text-sm text-foreground">
          {nodeData.label || 'Sequence'}
        </span>
      </div>
      
      <Handle 
        type="source" 
        position={Position.Bottom} 
        className="w-3 h-3 bg-blue-500 border-2 border-background"
      />
    </div>
  );
});

SequenceNode.displayName = 'SequenceNode';

export { SequenceNode };