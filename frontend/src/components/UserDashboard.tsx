import { FC, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../api';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { Loading } from './Loading';

export const UserDashboard: FC = () => {
    const { account } = useTonConnectUI();
    const [stats, setStats] = useState<User | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (account?.address) {
            setLoading(true);
            api.getUserStats(account.address)
                .then((data) => setStats(data))
                .catch(console.error)
                .finally(() => setLoading(false));
        }
    }, [account]);

    if (loading) return <Loading />;
    if (!stats) return null;

    return (
        <div className="user-dashboard">
            <h2>Your Stats</h2>
            <div className="stats-grid">
                <div className="stat-item">
                    <label>Points</label>
                    <span className="stat-value">{stats.points}</span>
                </div>
                <div className="stat-item">
                    <label>TETRIX Balance</label>
                    <span className="stat-value">{stats.tetrix_balance}</span>
                </div>
                <div className="stat-item">
                    <label>Invite Slots</label>
                    <span className="stat-value">{stats.invite_slots}</span>
                </div>
                <div className="stat-item">
                    <label>Total Invites</label>
                    <span className="stat-value">{stats.total_invites}</span>
                </div>
                <div className="stat-item">
                    <label>Point Multiplier</label>
                    <span className="stat-value">{stats.point_multiplier}x</span>
                </div>
            </div>
        </div>
    );
}; 