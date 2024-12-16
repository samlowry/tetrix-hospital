import { useCallback, useEffect, useRef, useState } from 'react';
import { useTonConnectUI, useTonWallet } from '@tonconnect/ui-react';
import { useInterval } from '../hooks/useInterval';
import { api } from '../api';

export function TonConnect() {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();
    const wallet = useTonWallet();
    const [authorized, setAuthorized] = useState(false);

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
    useInterval(recreateProofPayload, api.refreshIntervalMs);

    // Handle wallet connection
    useEffect(() => {
        if (!wallet) {
            api.reset();
            setAuthorized(false);
            return;
        }

        const checkProof = async () => {
            if (wallet.connectItems?.tonProof && 'proof' in wallet.connectItems.tonProof) {
                await api.connectWallet({
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
            }

            if (!api.accessToken) {
                tonConnectUI.disconnect();
                setAuthorized(false);
                return;
            }

            setAuthorized(true);
        };

        checkProof();
    }, [wallet, tonConnectUI]);

    if (!authorized) {
        return null;
    }

    return (
        <div style={{ display: 'none' }}>
            {/* Hidden component that maintains the connection */}
            Connected and authorized
        </div>
    );
} 