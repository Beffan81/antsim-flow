import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Brain, AlertCircle, Save, RotateCcw, Download, Upload } from 'lucide-react';
import { PluginsResponse } from '@/lib/api-client';
import { useRef } from 'react';

interface BehaviorTree {
  root: any;
}

interface BehaviorEditorProps {
  tree: BehaviorTree;
  onChange: (tree: BehaviorTree) => void;
  onReset?: () => void;
  onExport?: () => void;
  onImport?: (file: File) => Promise<BehaviorTree>;
  plugins?: PluginsResponse;
  autoSaveEnabled?: boolean;
}

export const BehaviorEditor = ({ 
  tree, 
  onChange, 
  onReset, 
  onExport, 
  onImport, 
  plugins, 
  autoSaveEnabled = false 
}: BehaviorEditorProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && onImport) {
      try {
        await onImport(file);
      } catch (error) {
        console.error('Import failed:', error);
      }
    }
    // Reset the input so the same file can be selected again
    event.target.value = '';
  };
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

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          {onReset && (
            <Button variant="outline" size="sm" onClick={onReset}>
              <RotateCcw className="h-4 w-4 mr-1" />
              Reset to Default
            </Button>
          )}
          {onExport && (
            <Button variant="outline" size="sm" onClick={onExport}>
              <Download className="h-4 w-4 mr-1" />
              Export JSON
            </Button>
          )}
          {onImport && (
            <>
              <Button variant="outline" size="sm" onClick={handleImportClick}>
                <Upload className="h-4 w-4 mr-1" />
                Import JSON
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
            </>
          )}
        </div>

        {/* Current tree preview */}
        <div className="border rounded-lg p-4 bg-muted/50">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium">Current Behavior Tree (JSON)</h4>
            <div className="text-xs text-muted-foreground">
              {autoSaveEnabled ? 'Auto-saved to browser' : 'Not persisted'}
            </div>
          </div>
          <pre className="text-xs bg-background p-3 rounded border overflow-auto max-h-40">
            {JSON.stringify(tree, null, 2)}
          </pre>
          <p className="text-xs text-muted-foreground mt-2">
            Visual editor coming in Step 4. Changes are automatically saved and restored on page reload.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};