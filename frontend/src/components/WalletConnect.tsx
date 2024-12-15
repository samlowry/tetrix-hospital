import { useEffect, useState } from 'react';
import { TonConnectButton, useTonWallet, useTonConnectUI, useIsConnectionRestored } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const wallet = useTonWallet();
    const [tonConnectUI] = useTonConnectUI();
    const isConnectionRestored = useIsConnectionRestored();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function verifyWallet() {
            if (!isConnectionRestored || !wallet?.account.address) {
                return;
            }

            try {
                setError(null);
                // Get challenge from backend
                const { challenge } = await api.getChallenge(wallet.account.address);
                
                // Sign challenge with wallet
                const signature = await tonConnectUI.connector.signMessage({
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
                tonConnectUI.disconnect();
            }
        }
        
        verifyWallet();
    }, [wallet, tonConnectUI, isConnectionRestored]);

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