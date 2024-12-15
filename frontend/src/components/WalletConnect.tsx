import { useEffect, useState } from 'react';
import { TonConnectButton, useTonConnect } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const { wallet, connector } = useTonConnect();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function verifyWallet() {
            if (wallet?.account.address) {
                try {
                    setError(null);
                    // Get challenge from backend
                    const { challenge } = await api.getChallenge(wallet.account.address);
                    
                    // Sign challenge with wallet
                    const signature = await connector.signMessage({
                        message: challenge
                    });
                    
                    // Verify signature and register wallet
                    await api.connectWallet({
                        address: wallet.account.address,
                        signature,
                        challenge
                    });
                    
                    console.log('Wallet verified and connected');
                } catch (error) {
                    console.error('Error verifying wallet:', error);
                    setError(error instanceof Error ? error.message : 'Failed to verify wallet');
                }
            }
        }
        
        verifyWallet();
    }, [wallet, connector]);

    return (
        <div className="wallet-connect">
            <TonConnectButton />
            {wallet && (
                <div className="wallet-info">
                    <p>Connected: {wallet.account.address}</p>
                </div>
            )}
            {error && (
                <div className="error-message" style={{ color: 'red', marginTop: '10px' }}>
                    {error}
                </div>
            )}
        </div>
    );
}; 