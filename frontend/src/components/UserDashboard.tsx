import { FC, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../api';
import { useTonWallet } from '@tonconnect/ui-react';
import { Loading } from './Loading';

export const UserDashboard: FC = () => {
    const wallet = useTonWallet();
    const [stats, setStats] = useState<User | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (wallet?.account.address) {
            setLoading(true);
            api.getUserStats(wallet.account.address)
                .then((data) => setStats(data))
                .catch(console.error)
                .finally(() => setLoading(false));
        }
    }, [wallet]);

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