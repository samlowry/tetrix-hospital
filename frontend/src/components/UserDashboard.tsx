import { FC, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../api';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { Loading } from './Loading';

export const UserDashboard: FC = () => {
    const [tonConnectUI] = useTonConnectUI();
    const [stats, setStats] = useState<User | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const handleStatusChange = async (wallet: any) => {
            if (!wallet?.account.address) {
                setStats(null);
                return;
            }

            setLoading(true);
            try {
                const data = await api.getUserStats(wallet.account.address);
                setStats(data);
            } catch (error) {
                console.error(error);
                setStats(null);
            } finally {
                setLoading(false);
            }
        };

        return tonConnectUI.onStatusChange(handleStatusChange);
    }, [tonConnectUI]);

    if (loading) return <Loading />;
    if (!stats) return null;

    return (
        <div>
            <h2>Your Stats</h2>
            <p>Points: {stats.points}</p>
            <p>Total Invites: {stats.total_invites}</p>
        </div>
    );
}; 