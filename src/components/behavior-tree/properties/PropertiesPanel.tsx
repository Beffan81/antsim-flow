import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Settings, AlertCircle } from 'lucide-react';
import { BehaviorTree } from '@/hooks/use-persisted-behavior-tree';
import { PluginsResponse } from '@/lib/api-client';

interface PropertiesPanelProps {
  selectedNodeId: string | null;
  tree: BehaviorTree;
  onChange: (tree: BehaviorTree) => void;
  plugins?: PluginsResponse;
}

export const PropertiesPanel = ({
  selectedNodeId,
  tree,
  onChange,
  plugins
}: PropertiesPanelProps) => {
  if (!selectedNodeId) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-4 border-b border-border">
          <h3 className="font-semibold text-sm text-foreground flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Properties
          </h3>
        </div>
        
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="text-center text-muted-foreground">
            <Settings className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Select a node to edit properties</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-border">
        <h3 className="font-semibold text-sm text-foreground flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Properties
        </h3>
        <p className="text-xs text-muted-foreground mt-1">
          Configure selected node
        </p>
      </div>
      
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Node Info */}
          <Card className="p-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Node ID</span>
                <Badge variant="outline" className="text-xs font-mono">
                  {selectedNodeId}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                Selected node identifier
              </div>
            </div>
          </Card>

          {/* Coming Soon Notice */}
          <Card className="p-3 bg-muted/50">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-muted-foreground mt-0.5" />
              <div>
                <div className="text-sm font-medium text-foreground">
                  Properties Editor Coming Soon
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  Advanced node configuration, parameter editing, and validation will be available in the next update.
                </div>
              </div>
            </div>
          </Card>

          {/* Plugin Context */}
          {plugins && (
            <Card className="p-3">
              <div className="space-y-2">
                <div className="text-sm font-medium">Available Plugins</div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">
                    Steps: {plugins.steps.length}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Triggers: {plugins.triggers.length}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Sensors: {plugins.sensors?.length || 0}
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};