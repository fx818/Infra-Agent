import api from './client';
import type { ProjectCreate, ProjectResponse } from '../types';

export const projectsApi = {
    getAll: async () => {
        const response = await api.get<ProjectResponse[]>('/projects/');
        return response.data;
    },

    getOne: async (id: string | number) => {
        const response = await api.get<ProjectResponse>(`/projects/${id}`);
        return response.data;
    },

    create: async (data: ProjectCreate) => {
        const response = await api.post<ProjectResponse>('/projects/', data);
        return response.data;
    },

    delete: async (id: string | number) => {
        await api.delete(`/projects/${id}`);
    }
};
