import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface AgentConfig {
  energy: number;
  max_energy: number;
  stomach_capacity: number;
  social_stomach_capacity: number;
  hunger_threshold: number;
}

interface AgentFormProps {
  config: AgentConfig;
  onChange: (config: AgentConfig) => void;
}

export const AgentForm = ({ config, onChange }: AgentFormProps) => {
  const updateField = (field: keyof AgentConfig, value: number) => {
    onChange({ ...config, [field]: value });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Configuration</CardTitle>
        <CardDescription>
          Configure the properties of individual ants in the simulation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            <p className="text-xs text-muted-foreground">Starting energy level</p>
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
            <p className="text-xs text-muted-foreground">Maximum energy capacity</p>
          </div>

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
            <p className="text-xs text-muted-foreground">Food storage capacity</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="social_stomach_capacity">Social Stomach</Label>
            <Input
              id="social_stomach_capacity"
              type="number"
              value={config.social_stomach_capacity}
              onChange={(e) => updateField('social_stomach_capacity', parseInt(e.target.value) || 0)}
              min="1"
              max="1000"
            />
            <p className="text-xs text-muted-foreground">Shared food storage</p>
          </div>

          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="hunger_threshold">Hunger Threshold</Label>
            <Input
              id="hunger_threshold"
              type="number"
              value={config.hunger_threshold}
              onChange={(e) => updateField('hunger_threshold', parseInt(e.target.value) || 0)}
              min="1"
              max="100"
            />
            <p className="text-xs text-muted-foreground">Energy level that triggers hunger behavior</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};