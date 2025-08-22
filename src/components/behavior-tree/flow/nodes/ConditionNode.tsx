import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { HelpCircle } from 'lucide-react';

interface ConditionNodeData {
  label?: string;
  condition?: {
    triggers: Array<{ name: string; params?: any }>;
    logic: 'AND' | 'OR';
  };
}

const ConditionNode = memo(({ data, selected }: NodeProps) => {
  const nodeData = data as ConditionNodeData;
  const triggerCount = nodeData.condition?.triggers?.length || 0;
  const logic = nodeData.condition?.logic || 'AND';
  
  return (
    <div className={`
      px-4 py-3 rounded-lg border-2 bg-gradient-to-br from-yellow-500/10 to-yellow-500/5 
      ${selected ? 'border-yellow-500 shadow-lg' : 'border-border'}
      transition-all duration-200 min-w-[140px]
    `}>
      <Handle 
        type="target" 
        position={Position.Top} 
        className="w-3 h-3 bg-yellow-500 border-2 border-background"
      />
      
      <div className="text-center">
        <div className="flex items-center gap-2 justify-center mb-1">
          <HelpCircle className="w-4 h-4 text-yellow-600" />
          <span className="font-medium text-sm text-foreground">
            {nodeData.label || 'Condition'}
          </span>
        </div>
        
        {triggerCount > 0 && (
          <div className="text-xs text-muted-foreground">
            {triggerCount} trigger{triggerCount !== 1 ? 's' : ''} ({logic})
          </div>
        )}
      </div>
      
      <Handle 
        type="source" 
        position={Position.Bottom} 
        className="w-3 h-3 bg-yellow-500 border-2 border-background"
      />
    </div>
  );
});

ConditionNode.displayName = 'ConditionNode';

export { ConditionNode };