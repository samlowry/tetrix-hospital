import { TonProofPayload } from '../api';

interface TonProof {
    sendTonProof: (data: { payload: string }) => Promise<TonProofPayload>;
}

declare global {
    interface Window {
        ton?: TonProof;
    }
}

export {}; 