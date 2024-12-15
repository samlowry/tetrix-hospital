import { useEffect, useState, useRef } from 'react';
import { TonConnectButton, useTonConnectUI } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const [{ connector }] = useTonConnectUI();
    const [error, setError] = useState<string | null>(null);
    const firstProofLoading = useRef<boolean>(true);

    useEffect(() => {
        const setupProof = async () => {
            if (firstProofLoading.current) {
                connector.setConnectRequestParameters({ state: 'loading' });
                firstProofLoading.current = false;
            }

            const { challenge } = await api.getChallenge("init");
            if (challenge) {
                connector.setConnectRequestParameters({ 
                    state: 'ready', 
                    value: challenge 
                });
            } else {
                connector.setConnectRequestParameters(null);
            }
        };

        setupProof();
    }, [connector]);

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
                        signature: wallet.connectItems.tonProof.proof,
                        challenge: wallet.connectItems.tonProof.payload
                    });
                } else {
                    setError('Wallet does not support TON Proof');
                    connector.disconnect();
                }
            } catch (e) {
                if (e instanceof Error) {
                    setError(e.message);
                } else {
                    setError('Failed to verify wallet');
                }
                connector.disconnect();
            }
        };

        return connector.onStatusChange(handleStatusChange);
    }, [connector]);

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