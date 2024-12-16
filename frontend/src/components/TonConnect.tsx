import { useCallback, useEffect, useRef } from 'react';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { useInterval } from '../hooks/useInterval';
import { api } from '../api';

export function TonConnect() {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();

    const generatePayload = useCallback(async () => {
        try {
            const { payload } = await api.getChallenge();
            console.log('Generated payload:', payload);
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
            console.log('Setting proof request:', payload);
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
        return tonConnectUI.onStatusChange(async (w) => {
            console.log('Wallet status changed:', w);
            if (!w) {
                api.reset();
                return;
            }

            if (w.connectItems?.tonProof && 'proof' in w.connectItems.tonProof) {
                console.log('Got proof from wallet:', w.connectItems.tonProof);
                try {
                    await api.connectWallet({
                        address: w.account.address,
                        proof: {
                            type: 'ton_proof',
                            domain: w.connectItems.tonProof.proof.domain,
                            timestamp: w.connectItems.tonProof.proof.timestamp,
                            payload: w.connectItems.tonProof.proof.payload,
                            signature: w.connectItems.tonProof.proof.signature,
                            state_init: w.account.walletStateInit,
                            public_key: w.account.publicKey
                        }
                    });
                } catch (error) {
                    console.error('Wallet verification failed:', error);
                    tonConnectUI.disconnect();
                }
            } else {
                console.log('No proof in wallet connection, requesting new proof');
                await recreateProofPayload();
            }
        });
    }, [tonConnectUI, recreateProofPayload]);

    return null;
} 