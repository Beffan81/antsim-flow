import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, Settings, Brain, Play, CheckCircle, AlertCircle, Server } from 'lucide-react';
import { usePlugins, useValidateConfig, useStartSimulation, useTestConnection } from '@/hooks/use-api';
import { useToast } from '@/hooks/use-toast';
import { EnvironmentForm } from '@/components/environment-form';
import { AgentForm } from '@/components/agent-form';
import { BehaviorEditor } from '@/components/behavior-editor';

const AntsimApp = () => {
  const { toast } = useToast();
  const [currentTab, setCurrentTab] = useState('environment');
  
  // API hooks
  const { data: plugins, isLoading: pluginsLoading, error: pluginsError } = usePlugins();
  const validateConfig = useValidateConfig();
  const startSimulation = useStartSimulation();
  const testConnection = useTestConnection();

  // Form data
  const [environmentConfig, setEnvironmentConfig] = useState({
    width: 100,
    height: 100,
    entry_positions: [[50, 50]] as number[][],
  });

  const [agentConfig, setAgentConfig] = useState({
    energy: 100,
    max_energy: 100,
    stomach_capacity: 50,
    social_stomach_capacity: 50,
    hunger_threshold: 30,
  });

  const [behaviorTree, setBehaviorTree] = useState({
    root: {
      type: 'step',
      name: 'dummy_step',
      step: {
        name: 'move',
        params: {},
      },
    },
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
    const config = {
      environment: environmentConfig,
      agent: agentConfig,
      behavior_tree: behaviorTree,
    };

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
    const config = {
      environment: environmentConfig,
      agent: agentConfig,
      behavior_tree: behaviorTree,
    };

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
              config={environmentConfig}
              onChange={setEnvironmentConfig}
            />
          </TabsContent>

          <TabsContent value="agent">
            <AgentForm 
              config={agentConfig}
              onChange={setAgentConfig}
            />
          </TabsContent>

          <TabsContent value="behavior">
            <BehaviorEditor 
              tree={behaviorTree}
              onChange={setBehaviorTree}
              plugins={plugins}
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