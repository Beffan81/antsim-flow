import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, Settings, Brain, Play, CheckCircle, AlertCircle, Server } from 'lucide-react';
import { usePlugins, useValidateConfig, useStartSimulation, useTestConnection } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { usePersistedBehaviorTree } from '@/hooks/use-persisted-behavior-tree';
import { EnvironmentForm } from '@/components/environment-form';
import { AgentForm } from '@/components/agent-form';
import { BehaviorEditor } from '@/components/behavior-editor';
import type { SimulationConfig } from '@/lib/api-client';
import defaultBehaviorTree from '@/data/default-behavior.json';

const AntsimApp = () => {
  const { toast } = useToast();
  const [currentTab, setCurrentTab] = useState('environment');
  
  // API hooks
  const { data: plugins, isLoading: pluginsLoading, error: pluginsError } = usePlugins();
  const validateConfig = useValidateConfig();
  const startSimulation = useStartSimulation();
  const testConnection = useTestConnection();
  
  // Persisted behavior tree hook
  const { tree: behaviorTree, saveTree, resetToDefault, exportTree, importTree, isLoaded } = usePersistedBehaviorTree(defaultBehaviorTree);

  // Initialize default configuration from provided JSON
  const [config, setConfig] = useState<SimulationConfig>({
    environment: {
      width: 50,
      height: 50,
      pheromone_evaporation_rate: 1,
      cell_size: 20,
      movement_directions: [
        [0, 1],
        [1, 0],
        [0, -1],
        [-1, 0]
      ],
      spiral: {
        max_steps: 100,
        directions: [
          [1, 0],
          [0, -1],
          [-1, 0],
          [0, 1]
        ],
        spiral_steps_before_warning: 100,
        spiral_distance_increment_factor_range: [1.2, 1.7],
        spiral_max_directions: 4
      },
      search: {
        max_distance: 20
      },
      entry_positions: [[25, 0]]
    },
    queen: {
      position: [25, 25],
      energy: 100,
      max_energy: 200,
      stomach_capacity: 150,
      pheromone_strength: 2,
      energy_increase_rate: 8,
      egg_laying_interval: 10,
      hunger_threshold: 20,
      hunger_pheromone_strength: 2,
      reduction_rate: 1,
      initial_energy_for_laying_eggs: 100,
      energy_after_laying_eggs: 50,
      stomach_depletion_rate: 1
    },
    brood: {
      energy: 50,
      max_energy: 100,
      stomach_capacity: 75,
      social_stomach_capacity: 0,
      pheromone_strength: 2,
      reduction_rate: 0.5,
      hunger_threshold: 30,
      hunger_pheromone_strength: 2,
      energy_increase_rate: 3,
      stomach_depletion_rate: 1
    },
    default_ant: {
      energy: 100,
      max_energy: 100,
      stomach_capacity: 100,
      social_stomach_capacity: 100,
      pheromone_strength: 2,
      reduction_rate: 1,
      hunger_threshold: 50,
      hunger_pheromone_strength: 2,
      energy_increase_rate: 5,
      stomach_depletion_rate: 1,
      behavior: {
        max_spiral_steps: 100,
        search_distance: 20,
        spiral_max_directions: 4
      },
      steps_map: {
        find_entry: "find_entry",
        move_to_entry: "move_to_entry",
        leave_nest: "leave_nest",
        enter_nest: "enter_nest",
        search_food_randomly: "search_food_randomly",
        follow_pheromone: "follow_pheromone",
        return_to_nest: "return_to_nest",
        feed_queen: "feed_queen",
        feed_brood: "feed_brood",
        random_move: "random_move",
        find_food_source: "find_food_source",
        collect_food: "collect_food",
        move_to_food: "move_to_food",
        explore_nest: "explore_nest",
        do_nothing: "do_nothing",
        feed_neighbor: "feed_neighbor",
        move_to_queen: "move_to_queen"
      },
      triggers_definitions: {
        social_hungry: { conditions: ["social_hungry"], logic: "AND" },
        not_social_hungry: { conditions: ["not_social_hungry"], logic: "AND" },
        individual_hungry: { conditions: ["individual_hungry"], logic: "AND" },
        not_individual_hungry: { conditions: ["not_individual_hungry"], logic: "AND" },
        in_nest: { conditions: ["in_nest"], logic: "AND" },
        not_in_nest: { conditions: ["not_in_nest"], logic: "AND" },
        at_entry: { conditions: ["at_entry"], logic: "AND" },
        not_at_entry: { conditions: ["not_at_entry"], logic: "AND" },
        food_detected: { conditions: ["food_detected"], logic: "AND" },
        individual_hungry_neighbor_found: { conditions: ["individual_hungry_neighbor_found"], logic: "AND" },
        neighbor_with_food_found: { conditions: ["neighbor_with_food_found"], logic: "AND" },
        SearchForFoodUnsuccessful: { conditions: ["search_unsuccessful"], logic: "AND" },
        queen_pheromone_detected: { conditions: ["queen_pheromone_detected"], logic: "AND" }
      },
      tasks: [
        {
          name: "FeedNeighbor",
          priority: 1,
          steps: ["feed_neighbor"],
          triggers: ["not_social_hungry", "individual_hungry_neighbor_found"],
          logic: "AND",
          max_retries: 3,
          max_cycles: 20,
          max_in_progress_per_step: 5
        },
        {
          name: "MutualFeedingResolver",
          priority: 0,
          steps: ["resolve_mutual_feeding"],
          triggers: ["not_social_hungry", "individual_hungry", "individual_hungry_neighbor_found"],
          logic: "AND",
          max_retries: 1,
          max_cycles: 5
        },
        {
          name: "GetFed",
          priority: 2,
          steps: ["do_nothing"],
          triggers: ["individual_hungry", "neighbor_with_food_found"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "EnterNest",
          priority: 3,
          steps: ["enter_nest"],
          triggers: ["not_social_hungry", "at_entry", "not_in_nest"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "FindEntry",
          priority: 2,
          steps: ["move_to_entry"],
          triggers: ["not_social_hungry", "not_at_entry", "not_in_nest"],
          logic: "AND",
          max_retries: 3,
          max_cycles: 15,
          max_in_progress_per_step: 5
        },
        {
          name: "FindExit",
          priority: 7,
          steps: ["move_to_entry"],
          triggers: ["social_hungry", "not_at_entry", "in_nest"],
          logic: "AND",
          max_retries: 3,
          max_cycles: 15,
          max_in_progress_per_step: 5
        },
        {
          name: "CollectFood",
          priority: 4,
          steps: ["move_to_food", "collect_food"],
          triggers: ["social_hungry", "not_in_nest", "food_detected"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "FindFood",
          priority: 5,
          steps: ["search_food_randomly", "move_to_food", "collect_food"],
          triggers: ["social_hungry", "not_in_nest"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "LeaveNest",
          priority: 6,
          steps: ["leave_nest"],
          triggers: ["social_hungry", "at_entry"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "ReturnToNest",
          priority: 4,
          steps: ["find_entry", "move_to_entry"],
          triggers: ["not_social_hungry", "not_in_nest", "SearchForFoodUnsuccessful"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "EnterNestGetFed",
          priority: 2,
          steps: ["enter_nest"],
          triggers: ["not_social_hungry", "at_entry", "SearchForFoodUnsuccessful"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "FeedQueenIfHungry",
          priority: 0,
          steps: ["move_to_queen", "feed_queen"],
          triggers: ["queen_pheromone_detected", "not_social_hungry"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "ExploreNest",
          priority: 99,
          steps: ["random_move"],
          triggers: ["in_nest"],
          logic: "AND",
          max_retries: 3
        },
        {
          name: "ReturnToNestWhenHungry",
          priority: -1,
          steps: ["find_entry", "move_to_entry", "enter_nest"],
          triggers: ["individual_hungry", "not_in_nest"],
          logic: "AND",
          max_retries: 3
        }
      ]
    },
    ants: {
      num_ants: 2
    },
    food_sources: [
      {
        position: [3, 3],
        amount: 1000
      },
      {
        position: [15, 15],
        amount: 1000
      }
    ],
    simulation: {
      screen_width: 1600,
      screen_height: 1200,
      cell_size: 20,
      colors: {
        background: [255, 255, 255],
        empty: [200, 200, 200],
        wall: [128, 128, 128],
        entry: [0, 255, 255],
        queen: [255, 0, 0],
        ant: [0, 0, 0],
        food: [0, 255, 0],
        pheromone: [255, 255, 0],
        dashboard_background: [50, 50, 50],
        text: [255, 255, 255]
      }
    },
    rates: {
      ant_energy_reduction_rate: 1,
      queen_energy_reduction_rate: 1
    },
    behavior_tree: behaviorTree
  });

  // Connection test
  const handleTestConnection = async () => {
    try {
      const result = await testConnection.mutateAsync();
      if (result) {
        toast({
          title: 'Connection Successful',
          description: 'Backend is running and accessible.',
        });
      } else {
        toast({
          title: 'Connection Failed',
          description: 'Cannot connect to backend. Make sure it\'s running on port 8000.',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Connection Error',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  // Validation
  const handleValidate = async () => {
    try {
      const result = await validateConfig.mutateAsync(config);
      if (result.ok) {
        toast({
          title: 'Validation Successful',
          description: 'Configuration is valid and ready to run.',
        });
      } else {
        const issues = [
          ...result.missing_steps.map(s => `Missing step: ${s}`),
          ...result.missing_triggers.map(t => `Missing trigger: ${t}`),
        ];
        toast({
          title: 'Validation Failed',
          description: result.error || issues.join(', '),
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Validation Error',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  // Start simulation
  const handleStart = async () => {
    try {
      const result = await startSimulation.mutateAsync({
        simulation: config,
        options: { format: 'json' },
      });

      if (result.ok && result.run_id) {
        toast({
          title: 'Simulation Started',
          description: `Run ID: ${result.run_id} (PID: ${result.pid})`,
        });
      } else {
        toast({
          title: 'Start Failed',
          description: result.error || 'Unknown error',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Start Error',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-4">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Antsim Behavior Tree Editor</h1>
          <p className="text-muted-foreground">Configure and run ant colony simulations</p>
        </div>

        {/* Connection Status */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Backend Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              {pluginsLoading ? (
                <Badge variant="secondary">
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                  Connecting...
                </Badge>
              ) : pluginsError ? (
                <Badge variant="destructive">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  Disconnected
                </Badge>
              ) : (
                <Badge variant="default">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              )}
              
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleTestConnection}
                disabled={testConnection.isPending}
              >
                {testConnection.isPending && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Test Connection
              </Button>
            </div>

            {/* Plugin Summary */}
            {plugins && (
              <div className="mt-4 text-sm text-muted-foreground">
                Loaded: {plugins.steps.length} steps, {plugins.triggers.length} triggers, {plugins.sensors.length} sensors
              </div>
            )}
          </CardContent>
        </Card>

        {/* Main Content */}
        <Tabs value={currentTab} onValueChange={setCurrentTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="environment" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Environment
            </TabsTrigger>
            <TabsTrigger value="agent" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Agent
            </TabsTrigger>
            <TabsTrigger value="behavior" className="flex items-center gap-2">
              <Brain className="h-4 w-4" />
              Behavior
            </TabsTrigger>
            <TabsTrigger value="actions" className="flex items-center gap-2">
              <Play className="h-4 w-4" />
              Actions
            </TabsTrigger>
          </TabsList>

          <TabsContent value="environment">
            <EnvironmentForm 
              config={config.environment}
              onChange={(env) => setConfig({...config, environment: env})}
            />
          </TabsContent>

          <TabsContent value="agent">
            <AgentForm 
              config={config.default_ant}
              onChange={(agent) => setConfig({...config, default_ant: agent})}
            />
          </TabsContent>

          <TabsContent value="behavior">
            <BehaviorEditor 
              tree={behaviorTree}
              onChange={saveTree}
              onReset={resetToDefault}
              onExport={exportTree}
              onImport={importTree}
              plugins={plugins}
              autoSaveEnabled={true}
            />
          </TabsContent>

          <TabsContent value="actions">
            <Card>
              <CardHeader>
                <CardTitle>Simulation Actions</CardTitle>
                <CardDescription>
                  Validate your configuration and start the simulation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={handleValidate}
                    disabled={validateConfig.isPending}
                  >
                    {validateConfig.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    Validate Config
                  </Button>
                  
                  <Button 
                    onClick={handleStart}
                    disabled={startSimulation.isPending}
                  >
                    {startSimulation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    Start Simulation
                  </Button>
                </div>

                {/* Backend not available warning */}
                {pluginsError && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Backend is not accessible. Make sure it's running with: <code>python start_backend.py</code>
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AntsimApp;