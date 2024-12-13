import { FC, useState, useEffect } from 'react';
import { TonConnectUIProvider } from '@tonconnect/ui-react';
import { WalletConnect } from './components/WalletConnect';
import { ProgressBar } from './components/ProgressBar';
import { UserDashboard } from './components/UserDashboard';
import { api } from './api';
import { Metrics } from './types';
import { GlobalStyles } from './styles/GlobalStyles';
import { ErrorBoundary } from './components/ErrorBoundary';

const App: React.FC = () => {
    const [metrics, setMetrics] = React.useState<Metrics | null>(null);

    React.useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const data = await api.getMetrics();
                setMetrics(data);
            } catch (error) {
                console.error('Error fetching metrics:', error);
            }
        };

        fetchMetrics();
        const interval = setInterval(fetchMetrics, 30000); // Update every 30s
        return () => clearInterval(interval);
    }, []);

    return (
        <ErrorBoundary>
            <TonConnectUIProvider manifestUrl="https://your-app.com/tonconnect-manifest.json">
                <GlobalStyles />
                <div className="app">
                    <header>
                        <h1>TETRIX Bot</h1>
                        <WalletConnect />
                    </header>
                    <main>
                        {metrics && <ProgressBar metrics={metrics} />}
                        <UserDashboard />
                    </main>
                </div>
            </TonConnectUIProvider>
        </ErrorBoundary>
    );
};

export default App; 