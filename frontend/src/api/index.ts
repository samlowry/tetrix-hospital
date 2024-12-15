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
            const response = await axios.post(`${API_URL}/api/generate_payload`);
            return handleResponse<{ payload: string }>(response);
        } catch (error) {
            return handleError(error as AxiosError);
        }
    },

    async connectWallet(data: { address: string; proof: TonProofPayload }): Promise<ConnectResponse> {
        try {
            const response = await axios.post(`${API_URL}/api/check_proof`, {
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