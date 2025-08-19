import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import type { DefaultAntConfig } from '@/lib/api-client';

interface AgentFormProps {
  config: DefaultAntConfig;
  onChange: (config: DefaultAntConfig) => void;
}

export const AgentForm = ({ config, onChange }: AgentFormProps) => {
  const updateField = (field: keyof DefaultAntConfig, value: any) => {
    onChange({ ...config, [field]: value });
  };

  const updateBehaviorField = (field: keyof DefaultAntConfig['behavior'], value: number) => {
    onChange({
      ...config,
      behavior: { ...config.behavior, [field]: value }
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Configuration</CardTitle>
        <CardDescription>
          Configure the properties and behavior of ants in the simulation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Energy Settings */}
        <div>
          <h3 className="font-medium mb-3">Energy & Health</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="energy">Energy</Label>
              <Input
                id="energy"
                type="number"
                value={config.energy}
                onChange={(e) => updateField('energy', parseInt(e.target.value) || 0)}
                min="1"
                max="1000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_energy">Max Energy</Label>
              <Input
                id="max_energy"
                type="number"
                value={config.max_energy}
                onChange={(e) => updateField('max_energy', parseInt(e.target.value) || 0)}
                min="1"
                max="1000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="hunger_threshold">Hunger Threshold</Label>
              <Input
                id="hunger_threshold"
                type="number"
                value={config.hunger_threshold}
                onChange={(e) => updateField('hunger_threshold', parseInt(e.target.value) || 0)}
                min="1"
                max="100"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="energy_increase_rate">Energy Increase Rate</Label>
              <Input
                id="energy_increase_rate"
                type="number"
                value={config.energy_increase_rate}
                onChange={(e) => updateField('energy_increase_rate', parseInt(e.target.value) || 0)}
                min="1"
                max="50"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Stomach Settings */}
        <div>
          <h3 className="font-medium mb-3">Food Storage</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stomach_capacity">Stomach Capacity</Label>
              <Input
                id="stomach_capacity"
                type="number"
                value={config.stomach_capacity}
                onChange={(e) => updateField('stomach_capacity', parseInt(e.target.value) || 0)}
                min="1"
                max="1000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="social_stomach_capacity">Social Stomach</Label>
              <Input
                id="social_stomach_capacity"
                type="number"
                value={config.social_stomach_capacity}
                onChange={(e) => updateField('social_stomach_capacity', parseInt(e.target.value) || 0)}
                min="0"
                max="1000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="stomach_depletion_rate">Depletion Rate</Label>
              <Input
                id="stomach_depletion_rate"
                type="number"
                value={config.stomach_depletion_rate}
                onChange={(e) => updateField('stomach_depletion_rate', parseInt(e.target.value) || 0)}
                min="1"
                max="10"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Pheromone Settings */}
        <div>
          <h3 className="font-medium mb-3">Pheromones</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="pheromone_strength">Pheromone Strength</Label>
              <Input
                id="pheromone_strength"
                type="number"
                value={config.pheromone_strength}
                onChange={(e) => updateField('pheromone_strength', parseInt(e.target.value) || 0)}
                min="1"
                max="10"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="hunger_pheromone_strength">Hunger Pheromone</Label>
              <Input
                id="hunger_pheromone_strength"
                type="number"
                value={config.hunger_pheromone_strength}
                onChange={(e) => updateField('hunger_pheromone_strength', parseInt(e.target.value) || 0)}
                min="1"
                max="10"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reduction_rate">Reduction Rate</Label>
              <Input
                id="reduction_rate"
                type="number"
                step="0.1"
                value={config.reduction_rate}
                onChange={(e) => updateField('reduction_rate', parseFloat(e.target.value) || 0)}
                min="0.1"
                max="5"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Behavior Settings */}
        <div>
          <h3 className="font-medium mb-3">Behavior Parameters</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_spiral_steps">Max Spiral Steps</Label>
              <Input
                id="max_spiral_steps"
                type="number"
                value={config.behavior.max_spiral_steps}
                onChange={(e) => updateBehaviorField('max_spiral_steps', parseInt(e.target.value) || 0)}
                min="1"
                max="1000"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="search_distance">Search Distance</Label>
              <Input
                id="search_distance"
                type="number"
                value={config.behavior.search_distance}
                onChange={(e) => updateBehaviorField('search_distance', parseInt(e.target.value) || 0)}
                min="1"
                max="100"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="spiral_max_directions">Max Spiral Directions</Label>
              <Input
                id="spiral_max_directions"
                type="number"
                value={config.behavior.spiral_max_directions}
                onChange={(e) => updateBehaviorField('spiral_max_directions', parseInt(e.target.value) || 0)}
                min="1"
                max="8"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Task Summary */}
        <div>
          <h3 className="font-medium mb-3">Behavior Summary</h3>
          <div className="text-sm text-muted-foreground space-y-1">
            <p>Tasks configured: {config.tasks.length}</p>
            <p>Steps mapped: {Object.keys(config.steps_map).length}</p>
            <p>Triggers defined: {Object.keys(config.triggers_definitions).length}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};