import { FC } from 'react';
import styled from 'styled-components';
import { WalletConnect } from './components/WalletConnect';
import { UserDashboard } from './components/UserDashboard';
import { useTonWallet } from '@tonconnect/ui-react';

const Container = styled.div`
    padding: 20px;
    max-width: 800px;
    margin: 0 auto;
`;

const Header = styled.header`
    margin-bottom: 30px;
    text-align: center;
`;

const Card = styled.div`
    background: var(--tg-theme-bg-color);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const App: FC = () => {
    const wallet = useTonWallet();

    return (
        <Container>
            <Header>
                <h1>TETRIX</h1>
            </Header>
            <Card>
                <h2>Connect Your Wallet</h2>
                <p className="hint-text">Use the button below to connect your TON wallet:</p>
                <WalletConnect />
            </Card>

            {wallet && (
                <Card>
                    <UserDashboard />
                </Card>
            )}
        </Container>
    );
};

export default App; 