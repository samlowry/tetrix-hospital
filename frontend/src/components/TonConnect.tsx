import { useCallback, useEffect, useRef } from 'react';
import { useTonConnectUI, TonProofItemReplySuccess } from '@tonconnect/ui-react';
import { useInterval } from '../hooks/useInterval';
import { api } from '../api';

const REFRESH_INTERVAL = 9 * 60 * 1000;

export function TonConnect() {
    const firstProofLoading = useRef<boolean>(true);
    const [tonConnectUI] = useTonConnectUI();

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

    const checkProof = useCallback(async (proof: TonProofItemReplySuccess['proof'], account: any) => {
        try {
            console.log('Checking proof:', { proof, account });
            const result = await api.connectWallet({
                address: account.address,
                proof: {
                    type: 'ton_proof',
                    domain: proof.domain,
                    timestamp: proof.timestamp,
                    payload: proof.payload,
                    signature: proof.signature,
                    state_init: account.walletStateInit,
                    public_key: account.publicKey
                }
            });
            
            if (result?.token) {
                localStorage.setItem('auth_token', result.token);
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