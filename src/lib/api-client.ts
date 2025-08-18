/**
 * API client for antsim backend
 * Handles communication with the FastAPI backend running on localhost:8000
 */

const API_BASE_URL = 'http://127.0.0.1:8000';

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

export interface SimulationConfig {
  environment: {
    width: number;
    height: number;
    entry_positions?: number[][];
  };
  agent: {
    energy?: number;
    max_energy?: number;
    stomach_capacity?: number;
    social_stomach_capacity?: number;
    hunger_threshold?: number;
  };
  behavior_tree: {
    root: any; // Will be defined more specifically in later steps
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