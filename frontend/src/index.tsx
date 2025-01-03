import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { TonConnectUIProvider } from '@tonconnect/ui-react';
import { GlobalStyles } from './styles/GlobalStyles';
import './patch-local-storage';

// Initialize Telegram Web App
declare global {
  interface Window {
    Telegram: {
      WebApp: any;
    };
  }
}

// Configure Telegram Web App
if (window.Telegram?.WebApp) {
  window.Telegram.WebApp.expand();
  window.Telegram.WebApp.enableClosingConfirmation();
}

// Add global styles
const style = document.createElement('style');
style.textContent = `
  body {
    margin: 0;
    padding: 0;
    background: var(--tg-theme-bg-color);
  }
  * {
    box-sizing: border-box;
  }
`;
document.head.appendChild(style);

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

const manifestUrl = `${import.meta.env.VITE_FRONTEND_URL}/tonconnect-manifest.json`;

// Debug info
console.log('Environment:', {
  mode: import.meta.env.MODE,
  manifestUrl,
  tgWebAppData: window.Telegram.WebApp.initData,
  tgWebAppVersion: window.Telegram.WebApp.version,
  tgPlatform: window.Telegram.WebApp.platform,
  tgTheme: window.Telegram.WebApp.colorScheme
});

// Tell Telegram that the Mini App is ready
window.Telegram.WebApp.ready();

root.render(
  <React.StrictMode>
    <GlobalStyles />
    <TonConnectUIProvider 
      manifestUrl={manifestUrl}
      restoreConnection={true}
      actionsConfiguration={{
        twaReturnUrl: 'https://t.me/tetrix_bot/app'
      }}
    >
      <App />
    </TonConnectUIProvider>
  </React.StrictMode>
); 