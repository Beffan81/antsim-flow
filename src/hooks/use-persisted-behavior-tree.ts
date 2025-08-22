import { usePersistedState } from './use-persisted-state';

export interface BehaviorTree {
  root: any;
}

// Validator for behavior tree structure
const isBehaviorTree = (value: any): value is BehaviorTree => {
  return value && typeof value === 'object' && 'root' in value && typeof value.root === 'object';
};

export function usePersistedBehaviorTree(defaultTree: BehaviorTree) {
  const [tree, setTree, { reset, isLoaded }] = usePersistedState(
    'antsim-behavior-tree',
    defaultTree,
    isBehaviorTree
  );

  const saveTree = (newTree: BehaviorTree) => {
    setTree(newTree);
  };

  const resetToDefault = () => {
    reset();
  };

  const exportTree = () => {
    const dataStr = JSON.stringify(tree, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'behavior-tree.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const importTree = (file: File): Promise<BehaviorTree> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          const parsed = JSON.parse(content);
          if (isBehaviorTree(parsed)) {
            setTree(parsed);
            resolve(parsed);
          } else {
            reject(new Error('Invalid behavior tree format'));
          }
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  };

  return {
    tree,
    saveTree,
    resetToDefault,
    exportTree,
    importTree,
    isLoaded
  };
}