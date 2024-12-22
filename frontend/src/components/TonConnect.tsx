import { useCallback, useEffect, useRef, useState } from 'react';
import { useTonConnectUI, useTonWallet } from '@tonconnect/ui-react';
import { api, TonProofPayload } from '../api';

export function TonConnect() {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();
    const wallet = useTonWallet();
    const [isConnected, setIsConnected] = useState(false);
    const [isValidated, setIsValidated] = useState(false);

    useEffect(() => {
        if (isValidated) {
            const timer = setTimeout(() => {
                window.Telegram.WebApp.close();
            }, 4000);
            return () => clearTimeout(timer);
        }
    }, [isValidated]);

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
        if (wallet && isConnected) {
            console.log('Found existing connection');
            firstProofLoading.current = false;
        }
    }, [wallet, isConnected]);

    useEffect(() => {
        if (firstProofLoading.current && !isConnected) {
            console.log('No existing connection, generating initial payload');
            recreateProofPayload();
        }
    }, [recreateProofPayload, isConnected]);

    // Запрашиваем новый пейлоад каждые 9 минут
    useEffect(() => {
        if (isConnected) return;
        
        const interval = setInterval(recreateProofPayload, 9 * 60 * 1000);
        return () => clearInterval(interval);
    }, [recreateProofPayload, isConnected]);

    useEffect(() => {
        return tonConnectUI.onStatusChange(async (w) => {
            console.log('Wallet status changed:', w);
            if (!w) {
                api.reset();
                setIsConnected(false);
                return;
            }

            if (wallet && isConnected && !w.connectItems?.tonProof) {
                console.log('Restored connection with existing token');
                return;
            }

            if (w.connectItems?.tonProof && 'proof' in w.connectItems.tonProof) {
                console.log('Got proof from wallet:', w.connectItems.tonProof);
                try {
                    const proof: TonProofPayload = {
                        type: 'ton_proof' as const,
                        domain: {
                            lengthBytes: 25,
                            value: new URL(import.meta.env.VITE_FRONTEND_URL).host
                        },
                        timestamp: w.connectItems.tonProof.proof.timestamp,
                        payload: w.connectItems.tonProof.proof.payload,
                        signature: w.connectItems.tonProof.proof.signature,
                        state_init: w.account.walletStateInit,
                        public_key: w.account.publicKey
                    };

                    // Single proof verification - backend handles the rest
                    const response = await api.connectWallet({
                        address: w.account.address,
                        proof
                    });

                    if (!response.token) {
                        throw new Error('Failed to verify wallet connection');
                    }

                    // Handle registration flow response
                    setIsConnected(true);
                    setIsValidated(true);

                    // Close webapp only for early backers
                    if (response.status === 'early_backer') {
                        setTimeout(() => {
                            window.Telegram.WebApp.close();
                        }, 4000);
                    }

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
                }
            } else if (!isConnected) {
                console.log('No proof in wallet connection, requesting new proof');
                await recreateProofPayload();
            }
        });
    }, [tonConnectUI, recreateProofPayload, wallet, isConnected]);

    return null;
} 