import axios, { AxiosError } from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const handleError = (error: AxiosError) => {
    if (error.response) {
        throw new Error(error.response.data.error || 'API Error');
    }
    throw error;
};

export const api = {
    async connectWallet(address: string) {
        try {
            const response = await axios.post(`${API_URL}/register-user`, {
                wallet_address: address
            });
            return response.data;
        } catch (error) {
            handleError(error as AxiosError);
        }
    },

    async getUserStats(address: string) {
        const response = await axios.get(`${API_URL}/user/${address}/stats`);
        return response.data;
    },

    async getMetrics() {
        const response = await axios.get(`${API_URL}/get-metrics`);
        return response.data;
    },

    async getLeaderboard(type: 'points' | 'invites') {
        const response = await axios.get(`${API_URL}/leaderboard/${type}`);
        return response.data;
    }
}; 