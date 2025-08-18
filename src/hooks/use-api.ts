import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, SimulationConfig, StartPayload } from '@/lib/api-client';

// Query keys for react-query caching
export const queryKeys = {
  plugins: ['plugins'] as const,
  status: (runId: string) => ['status', runId] as const,
};

/**
 * Hook to fetch available plugins
 */
export const usePlugins = () => {
  return useQuery({
    queryKey: queryKeys.plugins,
    queryFn: () => apiClient.fetchPlugins(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
  });
};

/**
 * Hook to validate simulation config
 */
export const useValidateConfig = () => {
  return useMutation({
    mutationFn: (config: SimulationConfig) => apiClient.validateConfig(config),
  });
};

/**
 * Hook to start simulation
 */
export const useStartSimulation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (payload: StartPayload) => apiClient.startSimulation(payload),
    onSuccess: () => {
      // Invalidate plugins query in case new plugins were discovered
      queryClient.invalidateQueries({ queryKey: queryKeys.plugins });
    },
  });
};

/**
 * Hook to get simulation status
 */
export const useSimulationStatus = (runId: string | null, enabled = true) => {
  return useQuery({
    queryKey: queryKeys.status(runId || ''),
    queryFn: () => apiClient.getStatus(runId!),
    enabled: !!runId && enabled,
    refetchInterval: 2000, // Poll every 2 seconds when active
    retry: false, // Don't retry status calls
  });
};

/**
 * Hook to stop simulation
 */
export const useStopSimulation = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (runId: string) => apiClient.stopSimulation(runId),
    onSuccess: (_, runId) => {
      // Invalidate the status query for this run
      queryClient.invalidateQueries({ queryKey: queryKeys.status(runId) });
    },
  });
};

/**
 * Hook to test backend connection
 */
export const useTestConnection = () => {
  return useMutation({
    mutationFn: () => apiClient.testConnection(),
  });
};