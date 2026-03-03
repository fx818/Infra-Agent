import api from './client';
import type { DeploymentResponse } from '../types';

export const deploymentApi = {
    deploy: async (projectId: string | number) => {
        const response = await api.post<DeploymentResponse>(`/projects/${projectId}/deploy`, {
            action: 'apply'
        });
        return response.data;
    },

    destroy: async (projectId: string | number) => {
        const response = await api.post<DeploymentResponse>(`/projects/${projectId}/destroy`, {
            action: 'destroy'
        });
        return response.data;
    },

    getStatus: async (projectId: string | number) => {
        const response = await api.get<DeploymentResponse>(`/projects/${projectId}/status`);
        return response.data;
    },

    list: async (projectId: string | number) => {
        const response = await api.get<DeploymentResponse[]>(`/projects/${projectId}/deployments`);
        return response.data;
    },

    getEC2Keys: async (projectId: string | number): Promise<{ keys: EC2KeyInfo[] }> => {
        const response = await api.get(`/projects/${projectId}/ec2-keys`);
        return response.data;
    },
};

export interface EC2KeyInfo {
    instance_id: string;
    label: string;
    key_pair_name: string;
    key_pair_id: string;
    has_pem: boolean;
    public_ip: string;
    public_dns: string;
}
