import apiClient from './client';

export interface LogDate {
    date: string;
    filename: string;
    size_bytes: number;
}

export interface LogRow {
    _id: number;
    timestamp: string;
    method: string;
    path: string;
    query_params: string;
    status_code: string;
    duration_ms: string;
    user_agent: string;
    request_body: string;
    response_body: string;
    error: string;
}

export interface LogsResponse {
    date: string;
    total: number;
    offset: number;
    limit: number;
    rows: LogRow[];
}

export interface LogsFilter {
    method?: string;
    status?: string;
    path?: string;
    limit?: number;
    offset?: number;
}

export const logsApi = {
    getDates: async (): Promise<LogDate[]> => {
        const { data } = await apiClient.get('/logs/dates');
        return data;
    },

    getLogs: async (date: string, filters: LogsFilter = {}): Promise<LogsResponse> => {
        const params: Record<string, any> = {};
        if (filters.method) params.method = filters.method;
        if (filters.status) params.status = filters.status;
        if (filters.path) params.path = filters.path;
        if (filters.limit !== undefined) params.limit = filters.limit;
        if (filters.offset !== undefined) params.offset = filters.offset;

        const { data } = await apiClient.get(`/logs/${date}`, { params });
        return data;
    },
};
