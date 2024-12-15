import { useEffect } from 'react';
import { TonConnectButton } from '@tonconnect/ui-react';
import { useTonConnect } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const { wallet, connector } = useTonConnect();

    useEffect(() => {
        async function verifyWallet() {
            if (wallet?.account.address) {
                try {
                    // Get challenge from backend
                    const { challenge } = await api.getChallenge(wallet.account.address);
                    
                    // Sign challenge with wallet
                    const signature = await connector.signMessage({
                        message: challenge
                    });
                    
                    // Verify signature and register wallet
                    await api.connectWallet({
                        address: wallet.account.address,
                        signature,
                        challenge
                    });
                    
                    console.log('Wallet verified and connected');
                } catch (error) {
                    console.error('Error verifying wallet:', error);
                }
            }
        }
        
        verifyWallet();
    }, [wallet, connector]);

    return (
        <div className="wallet-connect">
            <TonConnectButton />
            {wallet && (
                <div className="wallet-info">
                    <p>Connected: {wallet.account.address}</p>
                </div>
            )}
        </div>
    );
}; 