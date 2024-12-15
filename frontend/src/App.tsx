import { FC } from 'react';
import { TonConnectButton } from '@tonconnect/ui-react';
import styled from 'styled-components';

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

const TestInfo = styled.div`
    margin-top: 20px;
    padding: 20px;
    background: var(--tg-theme-secondary-bg-color);
    border-radius: 10px;
    
    .url-display {
        word-break: break-all;
        font-size: 14px;
        background: var(--tg-theme-bg-color);
        padding: 10px;
        border-radius: 4px;
        margin-top: 10px;
    }
`;

const App: FC = () => {
    // Extract base URL without query parameters
    const baseUrl = window.location.origin + window.location.pathname;

    return (
        <Container>
            <Title>TETRIX Bot</Title>
            
            <Card>
                <h2>Connect Your Wallet</h2>
                <p className="hint-text">Use the button below to connect your TON wallet:</p>
                <TonConnectButton />
            </Card>

            <TestInfo>
                <h3>Test Mode</h3>
                <p className="hint-text">Frontend is running and accessible through Cloudflare Pages!</p>
                <div className="url-display">
                    Base URL: {baseUrl}
                </div>
            </TestInfo>
        </Container>
    );
};

export default App; 