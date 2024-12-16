import { FC } from 'react';
import { useTonWallet } from '@tonconnect/ui-react';
import styled from 'styled-components';

const InfoPanel = styled.div`
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid var(--tg-theme-hint-color);
`;

const Address = styled.div`
    font-family: monospace;
    word-break: break-all;
    background: var(--tg-theme-secondary-bg-color);
    padding: 10px;
    border-radius: 8px;
    margin: 10px 0;
`;

const HintText = styled.p`
    color: var(--tg-theme-hint-color);
    font-size: 14px;
    margin-top: 10px;
`;

export const UserDashboard: FC = () => {
    const wallet = useTonWallet();

    if (!wallet) return null;

    return (
        <InfoPanel>
            <h3>Wallet Connected Successfully</h3>
            <Address>{wallet.account.address}</Address>
            <HintText>
                Please use the Telegram bot to register your wallet and start earning TETRIX tokens.
            </HintText>
        </InfoPanel>
    );
}; 