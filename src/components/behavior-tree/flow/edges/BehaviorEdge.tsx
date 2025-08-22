import { memo } from 'react';
import { BaseEdge, EdgeProps, getBezierPath } from '@xyflow/react';

const BehaviorEdge = memo(({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  selected,
}: EdgeProps) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <BaseEdge 
      path={edgePath} 
      className={`
        transition-all duration-200
        ${selected ? 'stroke-primary stroke-2' : 'stroke-muted-foreground stroke-1'}
      `}
    />
  );
});

BehaviorEdge.displayName = 'BehaviorEdge';

export { BehaviorEdge };