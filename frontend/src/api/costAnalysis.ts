import api from './client';
import type {
    CostQueryRequest,
    CostForecastRequest,
    CostAnalysisResponse,
} from '../types';

export const getCostSummary = async (params: CostQueryRequest): Promise<CostAnalysisResponse> => {
    const response = await api.post('/cost-analysis/summary', params);
    return response.data;
};

export const getCostForecast = async (params: CostForecastRequest): Promise<CostAnalysisResponse> => {
    const response = await api.post('/cost-analysis/forecast', params);
    return response.data;
};

export const getCostRecommendations = async (): Promise<CostAnalysisResponse> => {
    const response = await api.get('/cost-analysis/recommendations');
    return response.data;
};
