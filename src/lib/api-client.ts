/**
 * API client for antsim backend
 * Handles communication with the FastAPI backend running on localhost:8000
 */

// Auto-detect backend URL based on environment
const getBackendUrl = () => {
  // Check for environment variable first
  if (typeof window !== 'undefined' && (window as any).__ANTSIM_BACKEND_URL__) {
    return (window as any).__ANTSIM_BACKEND_URL__;
  }
  
  // In GitHub Codespaces, use the forwarded port URL
  if (typeof window !== 'undefined' && window.location.hostname.includes('app.github.dev')) {
    // Extract the base domain and create backend URL
    const hostname = window.location.hostname;
    const backendHostname = hostname.replace('-5173', '-8000');
    return `https://${backendHostname}`;
  }
  
  // Default to localhost for local development
  return 'http://127.0.0.1:8000';
};

const API_BASE_URL = getBackendUrl();

export interface PluginsResponse {
  steps: string[];
  triggers: string[];
  sensors: string[];
}

export interface ValidationResponse {
  ok: boolean;
  error?: string;
  missing_steps: string[];
  missing_triggers: string[];
  steps_referenced?: string[];
  triggers_referenced?: string[];
  steps_available?: string[];
  triggers_available?: string[];
}

export interface StartResponse {
  ok: boolean;
  run_id?: string;
  pid?: number;
  config_path?: string;
  error?: string;
}

export interface StatusResponse {
  state: 'running' | 'exited' | 'error';
  exit_code?: number;
  pid?: number;
  error?: string;
}

export interface StopResponse {
  ok: boolean;
  state?: 'exited' | 'running';
  exit_code?: number;
  pid?: number;
  error?: string;
}

export interface EnvironmentConfig {
  width: number;
  height: number;
  pheromone_evaporation_rate: number;
  cell_size: number;
  movement_directions: number[][];
  spiral: {
    max_steps: number;
    directions: number[][];
    spiral_steps_before_warning: number;
    spiral_distance_increment_factor_range: number[];
    spiral_max_directions: number;
  };
  search: {
    max_distance: number;
  };
  entry_positions?: number[][];
}

export interface QueenConfig {
  position: number[];
  energy: number;
  max_energy: number;
  stomach_capacity: number;
  pheromone_strength: number;
  energy_increase_rate: number;
  egg_laying_interval: number;
  hunger_threshold: number;
  hunger_pheromone_strength: number;
  reduction_rate: number;
  initial_energy_for_laying_eggs: number;
  energy_after_laying_eggs: number;
  stomach_depletion_rate: number;
}

export interface BroodConfig {
  energy: number;
  max_energy: number;
  stomach_capacity: number;
  social_stomach_capacity: number;
  pheromone_strength: number;
  reduction_rate: number;
  hunger_threshold: number;
  hunger_pheromone_strength: number;
  energy_increase_rate: number;
  stomach_depletion_rate: number;
}

export interface TaskConfig {
  name: string;
  priority: number;
  steps: string[];
  triggers: string[];
  logic: string;
  max_retries: number;
  max_cycles?: number;
  max_in_progress_per_step?: number;
}

export interface TriggerDefinition {
  conditions: string[];
  logic: string;
}

export interface DefaultAntConfig {
  energy: number;
  max_energy: number;
  stomach_capacity: number;
  social_stomach_capacity: number;
  pheromone_strength: number;
  reduction_rate: number;
  hunger_threshold: number;
  hunger_pheromone_strength: number;
  energy_increase_rate: number;
  stomach_depletion_rate: number;
  behavior: {
    max_spiral_steps: number;
    search_distance: number;
    spiral_max_directions: number;
  };
  steps_map: Record<string, string>;
  triggers_definitions: Record<string, TriggerDefinition>;
  tasks: TaskConfig[];
}

export interface AntsConfig {
  num_ants: number;
}

export interface FoodSource {
  position: number[];
  amount: number;
}

export interface SimulationDisplayConfig {
  screen_width: number;
  screen_height: number;
  cell_size: number;
  colors: {
    background: number[];
    empty: number[];
    wall: number[];
    entry: number[];
    queen: number[];
    ant: number[];
    food: number[];
    pheromone: number[];
    dashboard_background: number[];
    text: number[];
  };
}

export interface RatesConfig {
  ant_energy_reduction_rate: number;
  queen_energy_reduction_rate: number;
}

export interface SimulationConfig {
  environment: EnvironmentConfig;
  queen: QueenConfig;
  brood: BroodConfig;
  default_ant: DefaultAntConfig;
  ants: AntsConfig;
  food_sources: FoodSource[];
  simulation: SimulationDisplayConfig;
  rates: RatesConfig;
  behavior_tree?: {
    root: any;
  };
}

export interface StartPayload {
  simulation: SimulationConfig;
  options?: {
    format?: 'yaml' | 'json';
  };
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Get available plugins (steps, triggers, sensors)
   */
  async fetchPlugins(): Promise<PluginsResponse> {
    return this.request<PluginsResponse>('/plugins');
  }

  /**
   * Validate a simulation configuration
   */
  async validateConfig(config: SimulationConfig): Promise<ValidationResponse> {
    return this.request<ValidationResponse>('/validate', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  /**
   * Start a simulation
   */
  async startSimulation(payload: StartPayload): Promise<StartResponse> {
    return this.request<StartResponse>('/start', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Get status of a running simulation
   */
  async getStatus(runId: string): Promise<StatusResponse> {
    return this.request<StatusResponse>(`/status/${runId}`);
  }

  /**
   * Stop a running simulation
   */
  async stopSimulation(runId: string): Promise<StopResponse> {
    return this.request<StopResponse>(`/stop/${runId}`, {
      method: 'POST',
    });
  }

  /**
   * Test connection to backend
   */
  async testConnection(): Promise<boolean> {
    try {
      await this.fetchPlugins();
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing/custom instances
export { ApiClient };