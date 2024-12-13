import axios, { AxiosError, AxiosResponse } from 'axios';

interface ApiResponse<T> {
    data: T;
    status: number;
}

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const handleError = (error: AxiosError) => {
    if (error.response) {
        throw new Error(error.response.data.error || 'API Error');
    }
    throw error;
};

const handleResponse = <T>(response: AxiosResponse): T => response.data;

export const api = {
    async connectWallet(address: string) {
        try {
            const response = await axios.post(`${API_URL}/register-user`, {
                wallet_address: address
            });
            return handleResponse(response);
        } catch (error) {
            handleError(error as AxiosError);
        }
    },

    async getUserStats(address: string) {
        const response = await axios.get(`${API_URL}/user/${address}/stats`);
        return handleResponse(response);
    },

    async getMetrics() {
        const response = await axios.get(`${API_URL}/get-metrics`);
        return handleResponse(response);
    },

    async getLeaderboard(type: 'points' | 'invites') {
        const response = await axios.get(`${API_URL}/leaderboard/${type}`);
        return handleResponse(response);
    }
}; 