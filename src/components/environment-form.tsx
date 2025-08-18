import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Plus, Minus } from 'lucide-react';

interface EnvironmentConfig {
  width: number;
  height: number;
  entry_positions: number[][];
}

interface EnvironmentFormProps {
  config: EnvironmentConfig;
  onChange: (config: EnvironmentConfig) => void;
}

export const EnvironmentForm = ({ config, onChange }: EnvironmentFormProps) => {
  const updateField = (field: keyof EnvironmentConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const addEntryPosition = () => {
    const newPositions = [...config.entry_positions, [50, 50]];
    updateField('entry_positions', newPositions);
  };

  const removeEntryPosition = (index: number) => {
    const newPositions = config.entry_positions.filter((_, i) => i !== index);
    updateField('entry_positions', newPositions);
  };

  const updateEntryPosition = (index: number, axis: 0 | 1, value: number) => {
    const newPositions = [...config.entry_positions];
    newPositions[index][axis] = value;
    updateField('entry_positions', newPositions);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Environment Configuration</CardTitle>
        <CardDescription>
          Set up the simulation environment dimensions and ant entry points
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Dimensions */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="width">Width</Label>
            <Input
              id="width"
              type="number"
              value={config.width}
              onChange={(e) => updateField('width', parseInt(e.target.value) || 0)}
              min="10"
              max="1000"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="height">Height</Label>
            <Input
              id="height"
              type="number"
              value={config.height}
              onChange={(e) => updateField('height', parseInt(e.target.value) || 0)}
              min="10"
              max="1000"
            />
          </div>
        </div>

        {/* Entry Positions */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <Label className="text-base font-medium">Entry Positions</Label>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={addEntryPosition}
              className="flex items-center gap-1"
            >
              <Plus className="h-3 w-3" />
              Add Position
            </Button>
          </div>
          
          <div className="space-y-2">
            {config.entry_positions.map((position, index) => (
              <div key={index} className="flex items-center gap-2">
                <Label className="w-12 text-sm">#{index + 1}</Label>
                <div className="flex items-center gap-2">
                  <Label className="text-xs">X:</Label>
                  <Input
                    type="number"
                    value={position[0]}
                    onChange={(e) => updateEntryPosition(index, 0, parseInt(e.target.value) || 0)}
                    min="0"
                    max={config.width}
                    className="w-20"
                  />
                  <Label className="text-xs">Y:</Label>
                  <Input
                    type="number"
                    value={position[1]}
                    onChange={(e) => updateEntryPosition(index, 1, parseInt(e.target.value) || 0)}
                    min="0"
                    max={config.height}
                    className="w-20"
                  />
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => removeEntryPosition(index)}
                  disabled={config.entry_positions.length <= 1}
                  className="ml-auto"
                >
                  <Minus className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};