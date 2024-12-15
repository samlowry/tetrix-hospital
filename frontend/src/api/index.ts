import axios, { AxiosError, AxiosResponse } from 'axios';
import { User } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const handleError = (error: AxiosError) => {
    if (error.response?.data && typeof error.response.data === 'object' && 'error' in error.response.data) {
        throw new Error((error.response.data as { error: string }).error);
    }
    throw error;
};

const handleResponse = <T>(response: AxiosResponse<T>): T => response.data;

export const api = {
    async getChallenge(address: string) {
        try {
            const response = await axios.post(`${API_URL}/get-challenge`, {
                wallet_address: address
            });
            return handleResponse<{ challenge: string }>(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async connectWallet(data: { address: string; signature: string; challenge: string }) {
        try {
            const response = await axios.post(`${API_URL}/register-user`, {
                wallet_address: data.address,
                signature: data.signature,
                challenge: data.challenge
            });
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async getUserStats(address: string): Promise<User> {
        try {
            const response = await axios.get(`${API_URL}/user/${address}/stats`);
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async getMetrics() {
        try {
            const response = await axios.get(`${API_URL}/get-metrics`);
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async getLeaderboard(type: 'points' | 'invites') {
        try {
            const response = await axios.get(`${API_URL}/leaderboard/${type}`);
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    }
}; 