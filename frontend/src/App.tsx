import { FC } from 'react';
import { TonConnectButton } from '@tonconnect/ui-react';

const App: FC = () => {
    // Extract base URL without query parameters
    const baseUrl = window.location.origin + window.location.pathname;

    return (
        <div style={{ 
            padding: '20px', 
            maxWidth: '600px', 
            margin: '0 auto',
            fontFamily: 'Arial, sans-serif',
            background: '#FFFFFF',
            minHeight: '100vh',
            color: '#000000'
        }}>
            <h1 style={{ 
                color: '#000000', 
                background: '#FFFFFF',
                padding: '10px',
                borderRadius: '8px',
                marginBottom: '20px'
            }}>TETRIX Bot</h1>
            
            <div style={{ 
                background: '#FFFFFF',
                padding: '20px', 
                borderRadius: '10px',
                marginTop: '20px',
                border: '1px solid #E0E0E0',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
                <h2 style={{ color: '#000000' }}>Connect Your Wallet</h2>
                <p style={{ color: '#000000' }}>Use the button below to connect your TON wallet:</p>
                <TonConnectButton />
            </div>

            <div style={{ 
                marginTop: '20px', 
                padding: '20px', 
                background: '#FFFFFF',
                border: '1px solid #E0E0E0',
                borderRadius: '10px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
                <h3 style={{ color: '#000000' }}>Test Mode</h3>
                <p style={{ color: '#000000' }}>Frontend is running and accessible through ngrok!</p>
                <div style={{
                    color: '#000000',
                    wordBreak: 'break-all',
                    fontSize: '14px',
                    backgroundColor: '#f5f5f5',
                    padding: '10px',
                    borderRadius: '4px',
                    marginTop: '10px'
                }}>
                    Base URL: {baseUrl}
                </div>
            </div>
        </div>
    );
};

export default App; 