import { useCallback, useEffect, useRef, useState } from 'react';
import { useTonConnectUI, useTonWallet } from '@tonconnect/ui-react';
import { useInterval } from '../hooks/useInterval';
import { api, TonProofPayload } from '../api';

export function TonConnect() {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();
    const wallet = useTonWallet();
    const [isConnected, setIsConnected] = useState(() => {
        return !!api.accessToken;
    });
    const [showSuccess, setShowSuccess] = useState(false);

    useEffect(() => {
        if (showSuccess) {
            const timer = setTimeout(() => {
                window.Telegram.WebApp.close();
            }, 7000);
            return () => clearTimeout(timer);
        }
    }, [showSuccess]);

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

    useEffect(() => {
        if (wallet && api.accessToken) {
            console.log('Found existing connection');
            setIsConnected(true);
            firstProofLoading.current = false;
        }
    }, [wallet]);

    useEffect(() => {
        if (firstProofLoading.current && !isConnected) {
            console.log('No existing connection, generating initial payload');
            recreateProofPayload();
        }
    }, [recreateProofPayload, isConnected]);

    useInterval(recreateProofPayload, isConnected ? null : api.refreshIntervalMs);

    useEffect(() => {
        return tonConnectUI.onStatusChange(async (w) => {
            console.log('Wallet status changed:', w);
            if (!w) {
                api.reset();
                setIsConnected(false);
                return;
            }

            if (wallet && api.accessToken && !w.connectItems?.tonProof) {
                console.log('Restored connection with existing token');
                setIsConnected(true);
                return;
            }

            if (w.connectItems?.tonProof && 'proof' in w.connectItems.tonProof) {
                console.log('Got proof from wallet:', w.connectItems.tonProof);
                try {
                    const proof: TonProofPayload = {
                        type: 'ton_proof' as const,
                        domain: w.connectItems.tonProof.proof.domain,
                        timestamp: w.connectItems.tonProof.proof.timestamp,
                        payload: w.connectItems.tonProof.proof.payload,
                        signature: w.connectItems.tonProof.proof.signature,
                        state_init: w.account.walletStateInit,
                        public_key: w.account.publicKey
                    };

                    // Register user with TON Proof
                    await api.registerEarlyBacker(w.account.address, {
                        type: 'ton_proof',
                        domain: proof.domain,
                        timestamp: proof.timestamp,
                        payload: proof.payload,
                        signature: proof.signature,
                        state_init: proof.state_init,
                        public_key: proof.public_key
                    });

                    // Only show success and close if registration was successful
                    setIsConnected(true);
                    setShowSuccess(true);
                    window.Telegram.WebApp.showPopup({
                        title: 'Success!',
                        message: 'Wallet connected successfully. This window will close in 7 seconds.',
                        buttons: [{ type: 'ok' }]
                    });

                } catch (error) {
                    console.error('Wallet verification failed:', error);
                    window.Telegram.WebApp.showPopup({
                        title: 'Error',
                        message: error instanceof Error ? error.message : 'Connection failed',
                        buttons: [{ 
                            type: 'close',
                            text: 'Close'
                        }]
                    });
                    tonConnectUI.disconnect();
                    setIsConnected(false);
                    // Don't set showSuccess here since it failed
                }
            } else if (!isConnected) {
                console.log('No proof in wallet connection, requesting new proof');
                await recreateProofPayload();
            }
        });
    }, [tonConnectUI, recreateProofPayload, wallet, isConnected]);

    return null;
} 