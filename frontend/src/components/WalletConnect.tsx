import { useEffect, useState } from 'react';
import { TonConnectButton, useTonWallet } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const wallet = useTonWallet();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function verifyWallet() {
            if (wallet?.account.address) {
                try {
                    setError(null);
                    // Get challenge from backend
                    const { challenge } = await api.getChallenge(wallet.account.address);
                    
                    // Sign challenge with wallet
                    const signature = await wallet.connector.signMessage({
                        message: challenge
                    });
                    
                    // Verify signature and register wallet
                    await api.connectWallet({
                        address: wallet.account.address,
                        signature,
                        challenge
                    });
                } catch (e) {
                    if (e instanceof Error) {
                        setError(e.message);
                    } else {
                        setError('Failed to verify wallet');
                    }
                }
            }
        }
        
        verifyWallet();
    }, [wallet]);

    return (
        <div className="wallet-connect">
            <TonConnectButton />
            {wallet && (
                <div className="wallet-info">
                    <p>Connected: {wallet.account.address}</p>
                </div>
            )}
            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}
        </div>
    );
}; 