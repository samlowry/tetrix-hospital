import { useEffect, useState } from 'react';
import { TonConnectButton, useTonConnect } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const { connector } = useTonConnect();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const handleStatusChange = async (wallet: any) => {
            if (!wallet?.account.address) {
                return;
            }

            try {
                setError(null);
                if (wallet.connectItems?.tonProof && 'proof' in wallet.connectItems.tonProof) {
                    await api.connectWallet({
                        address: wallet.account.address,
                        signature: wallet.connectItems.tonProof.proof,
                        challenge: wallet.connectItems.tonProof.payload
                    });
                } else {
                    setError('Wallet does not support TON Proof');
                    connector.disconnect();
                }
            } catch (e) {
                if (e instanceof Error) {
                    setError(e.message);
                } else {
                    setError('Failed to verify wallet');
                }
                connector.disconnect();
            }
        };

        return connector.onStatusChange(handleStatusChange);
    }, [connector]);

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