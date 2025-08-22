import { BehaviorTreeEditor } from './behavior-tree/BehaviorTreeEditor';
import { PluginsResponse } from '@/lib/api-client';

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
  return (
    <BehaviorTreeEditor
      tree={tree}
      onChange={onChange}
      onReset={onReset}
      onExport={onExport}
      onImport={onImport}
      plugins={plugins}
      autoSaveEnabled={autoSaveEnabled}
    />
  );
};