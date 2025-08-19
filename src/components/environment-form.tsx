import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Plus, Minus } from 'lucide-react';
import type { EnvironmentConfig } from '@/lib/api-client';

interface EnvironmentFormProps {
  config: EnvironmentConfig;
  onChange: (config: EnvironmentConfig) => void;
}

export const EnvironmentForm = ({ config, onChange }: EnvironmentFormProps) => {
  const updateField = (field: keyof EnvironmentConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const addEntryPosition = () => {
    const newPositions = [...(config.entry_positions || []), [25, 0]];
    updateField('entry_positions', newPositions);
  };

  const removeEntryPosition = (index: number) => {
    const newPositions = (config.entry_positions || []).filter((_, i) => i !== index);
    updateField('entry_positions', newPositions);
  };

  const updateEntryPosition = (index: number, axis: 0 | 1, value: number) => {
    const newPositions = [...(config.entry_positions || [])];
    newPositions[index][axis] = value;
    updateField('entry_positions', newPositions);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Environment Configuration</CardTitle>
        <CardDescription>
          Set up the simulation environment with all parameters for ant behavior
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Basic Dimensions */}
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

        {/* Pheromone Settings */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="pheromone_evaporation_rate">Pheromone Evaporation Rate</Label>
            <Input
              id="pheromone_evaporation_rate"
              type="number"
              step="0.1"
              value={config.pheromone_evaporation_rate}
              onChange={(e) => updateField('pheromone_evaporation_rate', parseFloat(e.target.value) || 0)}
              min="0"
              max="10"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="cell_size">Cell Size</Label>
            <Input
              id="cell_size"
              type="number"
              value={config.cell_size}
              onChange={(e) => updateField('cell_size', parseInt(e.target.value) || 0)}
              min="1"
              max="100"
            />
          </div>
        </div>

        {/* Spiral Behavior */}
        <div className="space-y-4">
          <h3 className="font-medium">Spiral Behavior Settings</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="spiral_max_steps">Max Spiral Steps</Label>
              <Input
                id="spiral_max_steps"
                type="number"
                value={config.spiral.max_steps}
                onChange={(e) => updateField('spiral', {
                  ...config.spiral,
                  max_steps: parseInt(e.target.value) || 0
                })}
                min="1"
                max="1000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="spiral_warning">Warning Steps</Label>
              <Input
                id="spiral_warning"
                type="number"
                value={config.spiral.spiral_steps_before_warning}
                onChange={(e) => updateField('spiral', {
                  ...config.spiral,
                  spiral_steps_before_warning: parseInt(e.target.value) || 0
                })}
                min="1"
                max="1000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="spiral_max_directions">Max Directions</Label>
              <Input
                id="spiral_max_directions"
                type="number"
                value={config.spiral.spiral_max_directions}
                onChange={(e) => updateField('spiral', {
                  ...config.spiral,
                  spiral_max_directions: parseInt(e.target.value) || 0
                })}
                min="1"
                max="8"
              />
            </div>
          </div>
        </div>

        {/* Search Settings */}
        <div className="space-y-2">
          <Label htmlFor="search_max_distance">Search Max Distance</Label>
          <Input
            id="search_max_distance"
            type="number"
            value={config.search.max_distance}
            onChange={(e) => updateField('search', {
              ...config.search,
              max_distance: parseInt(e.target.value) || 0
            })}
            min="1"
            max="100"
          />
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
            {(config.entry_positions || []).map((position, index) => (
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
                  disabled={(config.entry_positions || []).length <= 1}
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