import api from './client';
import type { ArchitectureResponse, CostEstimate } from '../types';

export const architectureApi = {
    get: async (projectId: string | number) => {
        const response = await api.get<ArchitectureResponse>(`/projects/${projectId}/architecture`);
        return response.data;
    },

    generate: async (projectId: string | number, naturalLanguageInput: string) => {
        const response = await api.post<ArchitectureResponse>(`/projects/${projectId}/generate`, {
            natural_language_input: naturalLanguageInput
        });
        return response.data;
    },

    edit: async (projectId: string | number, modificationPrompt: string) => {
        const response = await api.post<ArchitectureResponse>(`/projects/${projectId}/edit`, {
            modification_prompt: modificationPrompt
        });
        return response.data;
    },

    getCost: async (projectId: string | number) => {
        const response = await api.get<CostEstimate>(`/projects/${projectId}/cost`);
        return response.data;
    },

    getMessages: async (projectId: string | number) => {
        const response = await api.get<any[]>(`/projects/${projectId}/messages`);
        return response.data;
    }
};
