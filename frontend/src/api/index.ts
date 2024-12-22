import axios, { AxiosError, AxiosResponse } from 'axios';

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

export interface User {
    telegram_id: number;
    wallet_address: string;
    points: number;
    invites_count: number;
}

export class ApiService {
    private baseURL = import.meta.env.VITE_BACKEND_URL;

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
            const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
            if (!telegram_id) {
                throw new Error('No Telegram ID found');
            }
            const response = await this.axiosInstance.post('/ton-connect/get-message', {
                telegram_id
            });
            const { message } = this.handleResponse<{ message: string }>(response);
            return { payload: message };
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    async connectWallet(data: { address: string; proof: TonProofPayload }): Promise<ConnectResponse> {
        try {
            const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
            if (!telegram_id) {
                throw new Error('No Telegram ID found');
            }
            const response = await this.axiosInstance.post('/ton-connect/proof', {
                telegram_id,
                wallet_address: data.address,
                payload: data.proof.payload
            });
            const result = this.handleResponse<{ success: boolean }>(response);
            if (result.success) {
                return {
                    token: 'dummy-token',  // Токен нам не нужен
                    status: 'early_backer'  // Всегда считаем early backer
                };
            }
            throw new Error('Failed to verify wallet');
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    async getUserStats(telegram_id: number): Promise<User> {
        try {
            const response = await this.axiosInstance.post('/api/users', {
                telegram_id
            });
            return this.handleResponse(response);
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    async getLeaderboard() {
        try {
            const response = await this.axiosInstance.get('/api/leaderboard');
            return this.handleResponse(response);
        } catch (error) {
            return this.handleError(error as AxiosError);
        }
    }

    reset() {
        // Ничего не делаем, так как токены не используются
    }
}

export const api = new ApiService(); 