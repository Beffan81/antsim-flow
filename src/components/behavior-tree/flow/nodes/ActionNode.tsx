import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Play } from 'lucide-react';

interface ActionNodeData {
  label?: string;
  step?: {
    name: string;
    params?: any;
  };
}

const ActionNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as ActionNodeData;
  const stepName = nodeData.step?.name || 'action';
  
  return (
    <div className={`
      px-4 py-3 rounded-lg border-2 bg-gradient-to-br from-green-500/10 to-green-500/5 
      ${selected ? 'border-green-500 shadow-lg' : 'border-border'}
      transition-all duration-200 min-w-[120px]
    `}>
      <Handle 
        type="target" 
        position={Position.Top} 
        className="w-3 h-3 bg-green-500 border-2 border-background"
      />
      
      <div className="text-center">
        <div className="flex items-center gap-2 justify-center mb-1">
          <Play className="w-4 h-4 text-green-600" />
          <span className="font-medium text-sm text-foreground">
            {nodeData.label || 'Action'}
          </span>
        </div>
        
        <div className="text-xs text-muted-foreground truncate">
          {stepName}
        </div>
      </div>
    </div>
  );
});

ActionNode.displayName = 'ActionNode';

export { ActionNode };