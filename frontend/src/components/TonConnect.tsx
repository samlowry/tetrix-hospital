import { useCallback, useEffect, useRef, useState } from 'react';
import { useTonConnectUI, useTonWallet } from '@tonconnect/ui-react';
import { useInterval } from '../hooks/useInterval';
import { api } from '../api';

export function TonConnect() {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();
    const wallet = useTonWallet();
    const [isConnected, setIsConnected] = useState(false);

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
        // Don't generate payload if already connected
        if (isConnected) {
            console.log('Already connected, skipping payload generation');
            return;
        }

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
    }, [tonConnectUI, generatePayload, isConnected]);

    // Initial payload generation only if not connected
    useEffect(() => {
        if (firstProofLoading.current && !isConnected) {
            recreateProofPayload();
        }
    }, [recreateProofPayload, isConnected]);

    // Refresh payload periodically only when not connected
    useInterval(recreateProofPayload, isConnected ? null : api.refreshIntervalMs);

    // Handle wallet connection
    useEffect(() => {
        return tonConnectUI.onStatusChange(async (w) => {
            console.log('Wallet status changed:', w);
            if (!w) {
                api.reset();
                setIsConnected(false);
                return;
            }

            // If we have a valid wallet connection, mark as connected
            if (wallet && !w.connectItems?.tonProof) {
                console.log('Restored connection without proof');
                setIsConnected(true);
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
                    setIsConnected(true);
                } catch (error) {
                    console.error('Wallet verification failed:', error);
                    tonConnectUI.disconnect();
                    setIsConnected(false);
                }
            } else {
                console.log('No proof in wallet connection, requesting new proof');
                await recreateProofPayload();
            }
        });
    }, [tonConnectUI, recreateProofPayload, wallet]);

    return null;
} 