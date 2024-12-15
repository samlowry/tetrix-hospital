import { useEffect, useState } from 'react';
import { TonConnectButton, useTonConnectUI } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const [tonConnectUI] = useTonConnectUI();
    const [error, setError] = useState<string | null>(null);

    // Handle wallet connection
    useEffect(() => {
        const handleStatusChange = async (wallet: any) => {
            if (!wallet?.account.address) {
                return;
            }

            try {
                setError(null);
                const { payload } = await api.getChallenge();

                // Set the connection parameters with proof request
                tonConnectUI.setConnectRequestParameters({
                    state: 'ready',
                    value: {
                        tonProof: payload
                    }
                });

                // Wait for proof from wallet
                if (!wallet.connectItems?.tonProof || !('proof' in wallet.connectItems.tonProof)) {
                    throw new Error('Failed to get proof from wallet');
                }

                const proof = wallet.connectItems.tonProof.proof;
                const result = await api.connectWallet({
                    address: wallet.account.address,
                    proof: {
                        type: 'ton_proof',
                        domain: proof.domain,
                        timestamp: proof.timestamp,
                        payload: proof.payload,
                        signature: proof.signature,
                        state_init: wallet.account.walletStateInit,
                        public_key: wallet.account.publicKey
                    }
                });

                if (!result?.token) {
                    throw new Error('Failed to verify wallet');
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