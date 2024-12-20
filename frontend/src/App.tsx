import { FC } from 'react';
import styled from 'styled-components';
import { WalletConnect } from './components/WalletConnect';
import { UserDashboard } from './components/UserDashboard';
import { useTonWallet } from '@tonconnect/ui-react';
import { TonConnect } from './components/TonConnect';

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
    background: var(--tg-theme-section-bg-color);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
`;

const App: FC = () => {
    const wallet = useTonWallet();

    return (
        <Container>
            <TonConnect />
            <Header>
                <h1>TETRIX</h1>
            </Header>
            <Card>
                <h2>Подключить кошелёк</h2>
                <p className="hint-text">Нажми кнопку ниже, чтобы подключить TON кошелёк:</p>
                <WalletConnect />
            </Card>

            {wallet && <UserDashboard />}
        </Container>
    );
};

export default App; 