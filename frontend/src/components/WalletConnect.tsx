import { useEffect, useState, useRef } from 'react';
import { TonConnectButton, useTonConnectUI } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const [tonConnectUI] = useTonConnectUI();
    const [error, setError] = useState<string | null>(null);
    const firstProofLoading = useRef<boolean>(true);

    useEffect(() => {
        const setupProof = async () => {
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

        setupProof();
    }, [tonConnectUI]);

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