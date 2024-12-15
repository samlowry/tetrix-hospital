import { FC } from 'react';
import styled from 'styled-components';
import { WalletConnect } from './components/WalletConnect';
import { UserDashboard } from './components/UserDashboard';
import { useTonConnect } from '@tonconnect/ui-react';

const Container = styled.div`
    padding: 20px;
    max-width: 600px;
    margin: 0 auto;
    min-height: 100vh;
`;

const Title = styled.h1`
    color: var(--tg-theme-text-color);
    margin-bottom: 20px;
`;

const Card = styled.div`
    background: var(--tg-theme-secondary-bg-color);
    padding: 20px;
    border-radius: 10px;
    margin-top: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const App: FC = () => {
    const { wallet } = useTonConnect();

    return (
        <Container>
            <Title>TETRIX Bot</Title>
            
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