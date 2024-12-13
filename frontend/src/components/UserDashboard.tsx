import { FC, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../api';
import { useTonConnect } from '@tonconnect/ui-react';
import { Loading } from './Loading';

export const UserDashboard: React.FC = () => {
    const { wallet } = useTonConnect();
    const [stats, setStats] = React.useState<User | null>(null);
    const [loading, setLoading] = React.useState(false);

    React.useEffect(() => {
        if (wallet?.account.address) {
            setLoading(true);
            api.getUserStats(wallet.account.address)
                .then(setStats)
                .catch(console.error)
                .finally(() => setLoading(false));
        }
    }, [wallet]);

    if (loading) return <Loading />;
    if (!stats) return null;

    return (
        <div className="user-dashboard">
            <h2>Your Stats</h2>
            <div className="stats-grid">
                <div className="stat-item">
                    <label>Points</label>
                    <value>{stats.points}</value>
                </div>
                <div className="stat-item">
                    <label>TETRIX Balance</label>
                    <value>{stats.tetrix_balance}</value>
                </div>
                <div className="stat-item">
                    <label>Invite Slots</label>
                    <value>{stats.invite_slots}</value>
                </div>
                <div className="stat-item">
                    <label>Total Invites</label>
                    <value>{stats.total_invites}</value>
                </div>
                <div className="stat-item">
                    <label>Point Multiplier</label>
                    <value>{stats.point_multiplier}x</value>
                </div>
            </div>
        </div>
    );
}; 