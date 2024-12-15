import { useEffect, useState, useRef } from 'react';
import { TonConnectButton, useTonConnectUI } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const [tonConnectUI] = useTonConnectUI();
    const [error, setError] = useState<string | null>(null);
    const firstProofLoading = useRef<boolean>(true);
    const refreshInterval = useRef<NodeJS.Timeout>();

    // Function to generate and set proof payload
    const recreateProofPayload = async () => {
        if (firstProofLoading.current) {
            tonConnectUI.setConnectRequestParameters({ state: 'loading' });
            firstProofLoading.current = false;
        }

        try {
            const { payload } = await api.getChallenge();
            if (payload) {
                tonConnectUI.setConnectRequestParameters({ 
                    state: 'ready',
                    value: { tonProof: payload }
                });
            } else {
                tonConnectUI.setConnectRequestParameters(null);
            }
        } catch (e) {
            console.error('Error setting up proof:', e);
            tonConnectUI.setConnectRequestParameters(null);
        }
    };

    // Setup periodic payload refresh
    useEffect(() => {
        recreateProofPayload();
        
        // Refresh payload every 9 minutes
        refreshInterval.current = setInterval(recreateProofPayload, 9 * 60 * 1000);

        return () => {
            if (refreshInterval.current) {
                clearInterval(refreshInterval.current);
            }
        };
    }, [tonConnectUI]);

    // Handle wallet connection
    useEffect(() => {
        const handleStatusChange = async (wallet: any) => {
            if (!wallet?.account.address) {
                return;
            }

            try {
                setError(null);
                if (wallet.connectItems?.tonProof && 'proof' in wallet.connectItems.tonProof) {
                    await api.connectWallet({
                        address: wallet.account.address,
                        proof: wallet.connectItems.tonProof
                    });
                } else {
                    setError('Wallet does not support TON Proof');
                    tonConnectUI.disconnect();
                }
            } catch (e) {
                if (e instanceof Error) {
                    setError(e.message);
                } else {
                    setError('Failed to verify wallet');
                }
                tonConnectUI.disconnect();
            }
        };

        return tonConnectUI.onStatusChange(handleStatusChange);
    }, [tonConnectUI]);

    return (
        <div className="wallet-connect">
            <TonConnectButton />
            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}
        </div>
    );
}; 