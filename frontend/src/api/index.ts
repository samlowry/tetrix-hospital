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
    status?: 'early_backer' | 'need_invite';
    message?: string;
    button?: string;
    replace_last?: boolean;
}

export class ApiService {
    private localStorageKey = 'tetrix-auth-token';
    private baseURL = import.meta.env.VITE_BACKEND_URL;
    public accessToken: string | null = null;
    public readonly refreshIntervalMs = 9 * 60 * 1000;

    constructor() {
        this.accessToken = localStorage.getItem(this.localStorageKey);
        
        // If no token is found, prepare for a new connection
        if (!this.accessToken) {
            this.getChallenge().catch(console.error);
        }
    }

    private get axiosInstance() {
        return axios.create({
            baseURL: this.baseURL,
            headers: {
                'ngrok-skip-browser-warning': 'true'
            }
        });
    }

    private handleError = (error: AxiosError) => {
        if (error.response?.data && typeof error.response.data === 'object' && 'error' in error.response.data) {
            throw new Error((error.response.data as { error: string }).error);
        }
        throw error;
    };

    private handleResponse = <T>(response: AxiosResponse<T>): T => response.data;

    async getChallenge() {
        try {
            const response = await this.axiosInstance.post('/api/generate_payload');
            return this.handleResponse<{ payload: string }>(response);
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    async connectWallet(data: { address: string; proof: TonProofPayload }): Promise<ConnectResponse> {
        try {
            const tgWebAppData = window.Telegram.WebApp.initData;
            const response = await this.axiosInstance.post('/api/check_proof', {
                address: data.address,
                proof: data.proof,
                public_key: data.proof.public_key,
                tg_init_data: tgWebAppData
            });
            const result = this.handleResponse<ConnectResponse>(response);
            if (result.token) {
                localStorage.setItem(this.localStorageKey, result.token);
                this.accessToken = result.token;
            }
            return result;
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    async getUserStats(telegram_id: number): Promise<User> {
        try {
            const response = await this.axiosInstance.post(`/api/user/stats`, {
                telegram_id
            });
            return this.handleResponse(response);
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    async getLeaderboard(type: 'points' | 'invites') {
        try {
            const response = await this.axiosInstance.get(`/api/user/leaderboard/${type}`);
            return this.handleResponse(response);
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    reset() {
        this.accessToken = null;
        localStorage.removeItem(this.localStorageKey);
        // Prepare for new connection immediately
        this.getChallenge().catch(console.error);
    }
}

export const api = new ApiService(); 