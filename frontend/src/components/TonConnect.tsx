import { useCallback, useEffect, useRef } from 'react';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { useInterval } from '../hooks/useInterval';

const REFRESH_INTERVAL = 9 * 60 * 1000; // 9 minutes

export function TonConnect() {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();

    const generatePayload = useCallback(async () => {
        try {
            const response = await fetch('/api/generate_payload', {
                method: 'POST',
            });
            const data = await response.json();
            return { tonProof: data.payload };
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

    const checkProof = useCallback(async (proof: any, account: any) => {
        try {
            console.log('Checking proof:', { proof, account });
            const reqBody = {
                address: account.address,
                network: account.chain,
                public_key: account.publicKey,
                proof: {
                    ...proof,
                    signature: proof.signature,
                    public_key: account.publicKey,
                    state_init: account.walletStateInit,
                    domain: {
                        lengthBytes: proof.domain.lengthBytes,
                        value: proof.domain.value
                    },
                    timestamp: proof.timestamp,
                    payload: proof.payload
                }
            };

            console.log('Sending proof request:', reqBody);

            const response = await fetch('/api/check_proof', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(reqBody),
            });

            const data = await response.json();
            if (data?.token) {
                localStorage.setItem('auth_token', data.token);
                return true;
            }
            return false;
        } catch (e) {
            console.error('Failed to check proof:', e);
            return false;
        }
    }, []);

    useEffect(() => {
        if (firstProofLoading.current) {
            recreateProofPayload();
        }
    }, [recreateProofPayload]);

    useInterval(recreateProofPayload, REFRESH_INTERVAL);

    useEffect(() => {
        return tonConnectUI.onStatusChange(async (w) => {
            if (!w) {
                localStorage.removeItem('auth_token');
                return;
            }

            if (w.connectItems?.tonProof && 'proof' in w.connectItems.tonProof) {
                console.log('Wallet connected with proof:', w.connectItems.tonProof);
                const success = await checkProof(w.connectItems.tonProof.proof, w.account);
                if (!success) {
                    tonConnectUI.disconnect();
                }
            }
        });
    }, [tonConnectUI, checkProof]);

    return null;
} 