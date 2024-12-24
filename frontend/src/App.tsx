import { FC } from 'react';
import styled from 'styled-components';
import { WalletConnect } from './components/WalletConnect';
import { UserDashboard } from './components/UserDashboard';
import { useTonWallet } from '@tonconnect/ui-react';
import { TonConnect } from './components/TonConnect';
import { LanguageProvider } from './i18n/LanguageContext';
import { LanguageSelector } from './components/LanguageSelector';
import { useLanguage } from './i18n/LanguageContext';

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

const AppContent: FC = () => {
    const wallet = useTonWallet();
    const { t } = useLanguage();

    return (
        <Container>
            <TonConnect />
            <Header>
                <h1>TETRIX</h1>
                <LanguageSelector />
            </Header>
            <Card>
                <h2>{t('connect_wallet.title')}</h2>
                <p className="hint-text">{t('connect_wallet.hint')}</p>
                <WalletConnect />
            </Card>

            {wallet && <UserDashboard />}
        </Container>
    );
};

const App: FC = () => {
    return (
        <LanguageProvider>
            <AppContent />
        </LanguageProvider>
    );
};

export default App; 