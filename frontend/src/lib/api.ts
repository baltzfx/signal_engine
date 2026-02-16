const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async query(message: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/query/custom?query=${encodeURIComponent(message)}`);
    if (!response.ok) {
      throw new Error('Query failed');
    }
    return response.json();
  }

  async getTopSymbols(count: number = 5): Promise<any> {
    const response = await fetch(`${this.baseUrl}/query/top-symbols?count=${count}`);
    if (!response.ok) {
      throw new Error('Failed to get top symbols');
    }
    return response.json();
  }

  async getSignals(limit: number = 50): Promise<any> {
    const response = await fetch(`${this.baseUrl}/signals?limit=${limit}`);
    if (!response.ok) {
      throw new Error('Failed to get signals');
    }
    return response.json();
  }

  async getPerformanceStats(lookbackDays: number = 7): Promise<any> {
    const response = await fetch(`${this.baseUrl}/performance/stats?lookback_days=${lookbackDays}`);
    if (!response.ok) {
      throw new Error('Failed to get performance stats');
    }
    return response.json();
  }

  async getHealth(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error('Failed to get health');
    }
    return response.json();
  }
}

export const apiClient = new ApiClient();
