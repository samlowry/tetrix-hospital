import axios, { AxiosError, AxiosResponse } from 'axios';
import { User } from '../types';

export interface TonProofPayload {
    type: 'ton_proof';
    domain: {
        lengthBytes: number;
        value: string;
    };
    timestamp: number;
    payload: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const handleError = (error: AxiosError) => {
    if (error.response?.data && typeof error.response.data === 'object' && 'error' in error.response.data) {
        throw new Error((error.response.data as { error: string }).error);
    }
    throw error;
};

const handleResponse = <T>(response: AxiosResponse<T>): T => response.data;

export const api = {
    async getChallenge() {
        try {
            const response = await axios.post(`${API_URL}/auth/get-challenge`);
            return handleResponse<{ payload: TonProofPayload }>(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async connectWallet(data: { address: string; proof: TonProofPayload }) {
        try {
            const response = await axios.post(`${API_URL}/auth/register-user`, {
                address: data.address,
                proof: data.proof
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
            const response = await axios.get(`${API_URL}/metrics`);
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async getLeaderboard(type: 'points' | 'invites') {
        try {
            const response = await axios.get(`${API_URL}/user/leaderboard/${type}`);
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    }
}; 