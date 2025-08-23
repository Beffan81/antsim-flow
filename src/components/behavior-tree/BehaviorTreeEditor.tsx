import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Brain, Code, Eye, Download, Upload, RotateCcw, BookOpen } from 'lucide-react';
import { BehaviorTreeFlow } from './flow/BehaviorTreeFlow';
import { ComponentPalette } from './palette/ComponentPalette';
import { PropertiesPanel } from './properties/PropertiesPanel';
import { BehaviorTree } from '@/hooks/use-persisted-behavior-tree';
import { PluginsResponse } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';

// Import behavior tree templates
import defaultBehaviorTree from '@/data/default-behavior.json';
import hungerSignalingMvp from '@/data/hunger-signaling-mvp.json';
import comprehensiveForaging from '@/data/comprehensive-foraging-behavior.json';

interface BehaviorTreeEditorProps {
  tree: BehaviorTree;
  onChange: (tree: BehaviorTree) => void;
  onReset?: () => void;
  onExport?: () => void;
  onImport?: (file: File) => Promise<BehaviorTree>;
  plugins?: PluginsResponse;
  autoSaveEnabled?: boolean;
}

const behaviorTemplates = [
  {
    id: 'default',
    name: 'Default Behavior',
    description: 'Original comprehensive ant behavior with feeding and foraging',
    tree: defaultBehaviorTree as BehaviorTree,
  },
  {
    id: 'hunger-signaling',
    name: 'Hunger Signaling MVP',
    description: 'Basic hunger signaling and feeding between ants',
    tree: hungerSignalingMvp as BehaviorTree,
  },
  {
    id: 'comprehensive-foraging',
    name: 'Comprehensive Foraging',
    description: 'Complete foraging behavior with social stomach management, nest navigation, and pheromone trails',
    tree: comprehensiveForaging as BehaviorTree,
  },
];

export const BehaviorTreeEditor = ({ 
  tree, 
  onChange, 
  onReset, 
  onExport, 
  onImport, 
  plugins, 
  autoSaveEnabled = false 
}: BehaviorTreeEditorProps) => {
  const { toast } = useToast();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [mode, setMode] = useState<'visual' | 'json'>('visual');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');

  const handleLoadTemplate = (templateId: string) => {
    const template = behaviorTemplates.find(t => t.id === templateId);
    if (template) {
      onChange(template.tree);
      toast({
        title: 'Template Loaded',
        description: `Loaded "${template.name}" behavior tree template.`,
      });
      setSelectedTemplate('');  // Reset selection
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          Behavior Tree Editor
        </CardTitle>
        <CardDescription>
          Design ant behavior using visual flowchart, JSON configuration, or pre-built templates
        </CardDescription>
        
        {/* Template Selection */}
        <div className="flex items-center gap-4 pt-2">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Templates:</span>
          </div>
          <Select value={selectedTemplate} onValueChange={handleLoadTemplate}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Load a behavior template..." />
            </SelectTrigger>
            <SelectContent>
              {behaviorTemplates.map((template) => (
                <SelectItem key={template.id} value={template.id}>
                  <div>
                    <div className="font-medium">{template.name}</div>
                    <div className="text-xs text-muted-foreground">{template.description}</div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <Separator />
        
        {/* Mode Selection */}
        <Tabs value={mode} onValueChange={(v) => setMode(v as 'visual' | 'json')} className="w-fit">
          <TabsList>
            <TabsTrigger value="visual" className="flex items-center gap-2">
              <Eye className="h-4 w-4" />
              Visual
            </TabsTrigger>
            <TabsTrigger value="json" className="flex items-center gap-2">
              <Code className="h-4 w-4" />
              JSON
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </CardHeader>
      
      <CardContent className="p-0 h-[calc(100%-120px)]">
        <Tabs value={mode} className="h-full">
          <TabsContent value="visual" className="h-full m-0 flex">
            <div className="flex h-full w-full">
              {/* Component Palette */}
              <div className="w-64 border-r border-border bg-muted/30">
                <ComponentPalette plugins={plugins} />
              </div>
              
              {/* Flow Canvas */}
              <div className="flex-1 relative">
                <BehaviorTreeFlow
                  tree={tree}
                  onChange={onChange}
                  selectedNodeId={selectedNodeId}
                  onNodeSelect={setSelectedNodeId}
                />
              </div>
              
              {/* Properties Panel */}
              <div className="w-80 border-l border-border bg-muted/30">
                <PropertiesPanel
                  selectedNodeId={selectedNodeId}
                  tree={tree}
                  onChange={onChange}
                  plugins={plugins}
                />
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="json" className="h-full m-0 p-4">
            <div className="h-full flex flex-col gap-4">
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
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => {
                      const input = document.createElement('input');
                      input.type = 'file';
                      input.accept = '.json';
                      input.onchange = async (e) => {
                        const file = (e.target as HTMLInputElement).files?.[0];
                        if (file) {
                          try {
                            await onImport(file);
                            toast({
                              title: 'Import Successful',
                              description: 'Behavior tree imported successfully.',
                            });
                          } catch (error) {
                            toast({
                              title: 'Import Failed',
                              description: error instanceof Error ? error.message : 'Failed to import file',
                              variant: 'destructive',
                            });
                          }
                        }
                      };
                      input.click();
                    }}
                  >
                    <Upload className="h-4 w-4 mr-1" />
                    Import JSON
                  </Button>
                )}
              </div>
              
              {/* JSON Editor */}
              <div className="flex-1 border rounded-lg bg-background">
                <div className="p-4 border-b">
                  <div className="flex justify-between items-center">
                    <h4 className="text-sm font-medium">Current Behavior Tree (JSON)</h4>
                    <div className="text-xs text-muted-foreground">
                      {autoSaveEnabled ? 'Auto-saved to browser' : 'Not persisted'}
                    </div>
                  </div>
                </div>
                <pre className="p-4 text-xs overflow-auto h-[calc(100%-60px)] whitespace-pre-wrap">
                  {JSON.stringify(tree, null, 2)}
                </pre>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};