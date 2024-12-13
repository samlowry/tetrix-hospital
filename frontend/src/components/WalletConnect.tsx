import React from 'react';
import { TonConnectButton } from '@tonconnect/ui-react';
import { useTonConnect } from '@tonconnect/ui-react';
import { api } from '../api';

export const WalletConnect: React.FC = () => {
    const { wallet } = useTonConnect();

    React.useEffect(() => {
        if (wallet?.account.address) {
            api.connectWallet(wallet.account.address)
                .then(response => {
                    console.log('Wallet connected:', response);
                })
                .catch(error => {
                    console.error('Error connecting wallet:', error);
                });
        }
    }, [wallet]);

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