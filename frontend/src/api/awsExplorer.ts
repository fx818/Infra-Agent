import api from './client';

export interface AWSResource {
    id: string;
    name: string;
    type: string;
    state: string;
    launch_time: string;
}

export interface AWSService {
    name: string;
    icon: string;
    count: number;
    resources: AWSResource[];
}

export interface AWSResourcesResponse {
    region: string;
    services: AWSService[];
    total_resources: number;
}

export interface AWSRegionsResponse {
    regions: string[];
}

export interface ResourceDeleteItem {
    service: string;
    resource_id: string;
    resource_name: string;
}

export interface ResourceDeleteResult {
    resource_id: string;
    resource_name: string;
    service: string;
    success: boolean;
    message: string;
}

export interface ResourceDeleteResponse {
    total: number;
    succeeded: number;
    failed: number;
    results: ResourceDeleteResult[];
}

export const awsExplorerApi = {
    getRegions: async (): Promise<AWSRegionsResponse> => {
        const response = await api.get<AWSRegionsResponse>('/aws/regions');
        return response.data;
    },

    getResources: async (region: string): Promise<AWSResourcesResponse> => {
        const response = await api.get<AWSResourcesResponse>('/aws/resources', {
            params: { region },
        });
        return response.data;
    },

    deleteResources: async (region: string, resources: ResourceDeleteItem[]): Promise<ResourceDeleteResponse> => {
        const response = await api.post<ResourceDeleteResponse>('/aws/resources/delete', {
            region,
            resources,
        });
        return response.data;
    },
};
