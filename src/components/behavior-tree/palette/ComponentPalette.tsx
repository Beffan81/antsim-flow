import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { 
  TreePine, 
  MoreHorizontal, 
  ArrowRight, 
  HelpCircle, 
  Play,
  Package
} from 'lucide-react';
import { PluginsResponse } from '@/lib/api-client';

interface ComponentPaletteProps {
  plugins?: PluginsResponse;
}

const controlFlowComponents = [
  {
    id: 'selector',
    label: 'Selector',
    icon: MoreHorizontal,
    description: 'Try children until one succeeds',
    color: 'text-orange-600',
    bgColor: 'bg-orange-500/10',
  },
  {
    id: 'sequence',
    label: 'Sequence',
    icon: ArrowRight,
    description: 'Execute children in order',
    color: 'text-blue-600',
    bgColor: 'bg-blue-500/10',
  },
  {
    id: 'condition',
    label: 'Condition',
    icon: HelpCircle,
    description: 'Check triggers/conditions',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-500/10',
  },
];

export const ComponentPalette = ({ plugins }: ComponentPaletteProps) => {
  const handleDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-border">
        <h3 className="font-semibold text-sm text-foreground flex items-center gap-2">
          <Package className="w-4 h-4" />
          Components
        </h3>
        <p className="text-xs text-muted-foreground mt-1">
          Drag components to canvas
        </p>
      </div>
      
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Control Flow Components */}
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Control Flow
            </h4>
            <div className="space-y-2">
              {controlFlowComponents.map((component) => (
                <Card
                  key={component.id}
                  className={`p-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-all duration-200 ${component.bgColor} border-dashed`}
                  draggable
                  onDragStart={(e) => handleDragStart(e, component.id)}
                >
                  <div className="flex items-center gap-2">
                    <component.icon className={`w-4 h-4 ${component.color}`} />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm text-foreground">
                        {component.label}
                      </div>
                      <div className="text-xs text-muted-foreground truncate">
                        {component.description}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          <Separator />

          {/* Plugin Actions */}
          {plugins && (
            <div className="space-y-3">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Actions ({plugins.steps.length})
              </h4>
              <div className="space-y-2">
                {plugins.steps.slice(0, 8).map((step) => (
                  <Card
                    key={step}
                    className="p-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-all duration-200 bg-green-500/10 border-dashed"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData('application/reactflow', 'action');
                      e.dataTransfer.setData('step-name', step);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <Play className="w-4 h-4 text-green-600" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-foreground">
                          {step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Step: {step}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
                
                {plugins.steps.length > 8 && (
                  <div className="text-xs text-muted-foreground text-center py-2">
                    +{plugins.steps.length - 8} more available
                  </div>
                )}
              </div>
            </div>
          )}

          <Separator />

          {/* Plugin Triggers (for reference) */}
          {plugins && plugins.triggers.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Available Triggers ({plugins.triggers.length})
              </h4>
              <div className="flex flex-wrap gap-1">
                {plugins.triggers.slice(0, 10).map((trigger) => (
                  <Badge key={trigger} variant="outline" className="text-xs">
                    {trigger}
                  </Badge>
                ))}
                {plugins.triggers.length > 10 && (
                  <Badge variant="outline" className="text-xs">
                    +{plugins.triggers.length - 10} more
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                Use in Condition nodes
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};