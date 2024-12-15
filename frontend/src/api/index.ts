import axios, { AxiosError, AxiosResponse } from 'axios';
import { User } from '../types';

export interface TonProofDomain {
    lengthBytes: number;
    value: string;
}

export interface TonProofPayload {
    type: 'ton_proof';
    domain: TonProofDomain;
    timestamp: number;
    payload: string;
    signature?: string;
    state_init?: string;
    public_key?: string;
}

export interface ConnectResponse {
    token: string;
}

const API_URL = 'https://5fa5-109-245-96-58.ngrok-free.app';

// Create axios instance with default headers
const axiosInstance = axios.create({
    baseURL: API_URL,
    headers: {
        'ngrok-skip-browser-warning': 'true'
    }
});

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
            const response = await axiosInstance.post('/api/generate_payload');
            return handleResponse<{ payload: string }>(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async connectWallet(data: { address: string; proof: TonProofPayload }): Promise<ConnectResponse> {
        try {
            const response = await axiosInstance.post('/api/check_proof', {
                address: data.address,
                proof: data.proof,
                public_key: data.proof.public_key
            });
            return handleResponse<ConnectResponse>(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async getUserStats(address: string): Promise<User> {
        try {
            const response = await axiosInstance.get(`/user/${address}/stats`);
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async getMetrics() {
        try {
            const response = await axiosInstance.get('/metrics');
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async getLeaderboard(type: 'points' | 'invites') {
        try {
            const response = await axiosInstance.get(`/user/leaderboard/${type}`);
            return handleResponse(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    }
}; 