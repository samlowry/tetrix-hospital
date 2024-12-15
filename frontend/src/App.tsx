import { FC, useEffect } from 'react';
import { TonConnectButton } from '@tonconnect/ui-react';
import styled from 'styled-components';

const Container = styled.div`
    padding: 20px;
    max-width: 600px;
    margin: 0 auto;
    min-height: 100vh;
`;

const Title = styled.h1`
    color: var(--text-color);
    margin-bottom: 20px;
`;

const Card = styled.div`
    background: var(--secondary-bg-color);
    padding: 20px;
    border-radius: 10px;
    margin-top: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
`;

const TestInfo = styled.div`
    margin-top: 20px;
    padding: 20px;
    background: var(--secondary-bg-color);
    border-radius: 10px;
    
    .url-display {
        word-break: break-all;
        font-size: 14px;
        background: var(--bg-color);
        padding: 10px;
        border-radius: 4px;
        margin-top: 10px;
    }
`;

const App: FC = () => {
    // Sync with Telegram theme changes
    useEffect(() => {
        const handleThemeChange = () => {
            document.documentElement.style.setProperty('--bg-color', window.Telegram.WebApp.themeParams.bg_color);
            document.documentElement.style.setProperty('--text-color', window.Telegram.WebApp.themeParams.text_color);
            document.documentElement.style.setProperty('--hint-color', window.Telegram.WebApp.themeParams.hint_color);
            document.documentElement.style.setProperty('--link-color', window.Telegram.WebApp.themeParams.link_color);
            document.documentElement.style.setProperty('--button-color', window.Telegram.WebApp.themeParams.button_color);
            document.documentElement.style.setProperty('--button-text-color', window.Telegram.WebApp.themeParams.button_text_color);
            document.documentElement.style.setProperty('--secondary-bg-color', window.Telegram.WebApp.themeParams.secondary_bg_color);
        };

        // Initial theme setup
        handleThemeChange();

        // Listen for theme changes
        window.Telegram.WebApp.onEvent('themeChanged', handleThemeChange);

        return () => {
            window.Telegram.WebApp.offEvent('themeChanged', handleThemeChange);
        };
    }, []);

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