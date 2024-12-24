import { TonConnectButton } from '@tonconnect/ui-react';
import { useLanguage } from '../i18n/LanguageContext';

export const WalletConnect = () => {
    const { t } = useLanguage();
    return <TonConnectButton />;
}; 