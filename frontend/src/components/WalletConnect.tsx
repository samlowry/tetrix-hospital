import { useCallback, useEffect, useRef, useState } from 'react';
import { TonConnectButton, useTonConnectUI } from '@tonconnect/ui-react';
import { api } from '../api';
import { useInterval } from '../hooks/useInterval';

const REFRESH_INTERVAL = 9 * 60 * 1000; // 9 minutes

export const WalletConnect: React.FC = () => {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();
    const [error, setError] = useState<string | null>(null);

    const generatePayload = useCallback(async () => {
        try {
            const { payload } = await api.getChallenge();
            return { tonProof: payload };
        } catch (e) {
            console.error('Failed to generate payload:', e);
            return null;
        }
    }, []);

    const recreateProofPayload = useCallback(async () => {
        if (firstProofLoading.current) {
            tonConnectUI.setConnectRequestParameters({ state: 'loading' });
            firstProofLoading.current = false;
        }

        const payload = await generatePayload();
        if (payload) {
            tonConnectUI.setConnectRequestParameters({ state: 'ready', value: payload });
        } else {
            tonConnectUI.setConnectRequestParameters(null);
        }
    }, [tonConnectUI, generatePayload]);

    // Initial payload generation
    useEffect(() => {
        if (firstProofLoading.current) {
            recreateProofPayload();
        }
    }, [recreateProofPayload]);

    // Refresh payload periodically
    useInterval(recreateProofPayload, REFRESH_INTERVAL);

    // Handle wallet connection
    useEffect(() => {
        return tonConnectUI.onStatusChange(async (wallet) => {
            if (!wallet) {
                setError(null);
                return;
            }

            try {
                if (wallet.connectItems?.tonProof && 'proof' in wallet.connectItems.tonProof) {
                    const result = await api.connectWallet({
                        address: wallet.account.address,
                        proof: {
                            type: 'ton_proof',
                            domain: wallet.connectItems.tonProof.proof.domain,
                            timestamp: wallet.connectItems.tonProof.proof.timestamp,
                            payload: wallet.connectItems.tonProof.proof.payload,
                            signature: wallet.connectItems.tonProof.proof.signature,
                            state_init: wallet.account.walletStateInit,
                            public_key: wallet.account.publicKey
                        }
                    });

                    if (!result?.token) {
                        throw new Error('Failed to verify wallet');
                    }
                } else {
                    throw new Error('Failed to get proof from wallet');
                }
            } catch (e) {
                if (e instanceof Error) {
                    setError(e.message);
                } else {
                    setError('Failed to verify wallet');
                }
                tonConnectUI.disconnect();
            }
        });
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