import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { TonConnectUIProvider } from '@tonconnect/ui-react';
import { GlobalStyles } from './styles/GlobalStyles';

// Add global styles
const style = document.createElement('style');
style.textContent = `
  body {
    margin: 0;
    padding: 0;
    background: #FFFFFF;
  }
  * {
    box-sizing: border-box;
  }
`;
document.head.appendChild(style);

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

const manifestUrl = 'https://tetrix-hospital.pages.dev/tonconnect-manifest.json';

// Debug info
console.log('Environment:', {
  mode: import.meta.env.MODE,
  manifestUrl,
  appUrl: import.meta.env.VITE_APP_URL
});

root.render(
  <React.StrictMode>
    <GlobalStyles />
    <TonConnectUIProvider 
      manifestUrl={manifestUrl}
      walletsList={{
        includeWallets: ['telegram-wallet'],
        excludeWallets: []
      }}
    >
      <App />
    </TonConnectUIProvider>
  </React.StrictMode>
); 