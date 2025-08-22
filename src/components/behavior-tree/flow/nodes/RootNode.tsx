import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { TreePine } from 'lucide-react';

interface RootNodeData {
  label: string;
}

const RootNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as { label?: string };
  return (
    <div className={`
      px-4 py-3 rounded-lg border-2 bg-gradient-to-br from-primary/10 to-primary/5 
      ${selected ? 'border-primary shadow-lg' : 'border-border'}
      transition-all duration-200
    `}>
      <div className="flex items-center gap-2">
        <TreePine className="w-5 h-5 text-primary" />
        <span className="font-medium text-sm text-foreground">
          {nodeData.label || 'Root'}
        </span>
      </div>
      
      <Handle 
        type="source" 
        position={Position.Bottom} 
        className="w-3 h-3 bg-primary border-2 border-primary-foreground"
      />
    </div>
  );
});

RootNode.displayName = 'RootNode';

export { RootNode };