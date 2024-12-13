export interface User {
    wallet_address: string;
    points: number;
    tetrix_balance: number;
    invite_slots: number;
    total_invites: number;
    point_multiplier: number;
}

export interface Metrics {
    holder_count: number;
    health: number;
    capitalization: number;
} 