import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Brain, AlertCircle } from 'lucide-react';
import { PluginsResponse } from '@/lib/api-client';

interface BehaviorTree {
  root: any;
}

interface BehaviorEditorProps {
  tree: BehaviorTree;
  onChange: (tree: BehaviorTree) => void;
  plugins?: PluginsResponse;
}

export const BehaviorEditor = ({ tree, onChange, plugins }: BehaviorEditorProps) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          Behavior Tree Editor
        </CardTitle>
        <CardDescription>
          Design the ant behavior using drag-and-drop flowchart (Coming in Step 4)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Plugin availability */}
        {plugins ? (
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-medium mb-2">Available Components</h4>
              <div className="flex flex-wrap gap-2">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Steps ({plugins.steps.length})</p>
                  <div className="flex flex-wrap gap-1">
                    {plugins.steps.slice(0, 5).map((step) => (
                      <Badge key={step} variant="secondary" className="text-xs">
                        {step}
                      </Badge>
                    ))}
                    {plugins.steps.length > 5 && (
                      <Badge variant="outline" className="text-xs">
                        +{plugins.steps.length - 5} more
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Triggers ({plugins.triggers.length})</p>
                <div className="flex flex-wrap gap-1">
                  {plugins.triggers.slice(0, 5).map((trigger) => (
                    <Badge key={trigger} variant="secondary" className="text-xs">
                      {trigger}
                    </Badge>
                  ))}
                  {plugins.triggers.length > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{plugins.triggers.length - 5} more
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              No plugins loaded. Make sure the backend is running.
            </AlertDescription>
          </Alert>
        )}

        {/* Current tree preview */}
        <div className="border rounded-lg p-4 bg-muted/50">
          <h4 className="text-sm font-medium mb-2">Current Behavior Tree (JSON)</h4>
          <pre className="text-xs bg-background p-3 rounded border overflow-auto max-h-40">
            {JSON.stringify(tree, null, 2)}
          </pre>
          <p className="text-xs text-muted-foreground mt-2">
            Visual editor coming in Step 4. For now, this shows the current tree structure.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};