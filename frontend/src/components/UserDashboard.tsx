import { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useTonAddress } from '@tonconnect/ui-react';
import { useLanguage } from '../i18n/LanguageContext';

const Card = styled.div`
  padding: 20px;
  background: var(--tg-theme-section-bg-color);
  border-radius: 12px;
  margin-bottom: 20px;
  color: var(--tg-theme-text-color);
`;

const Title = styled.h3`
  color: var(--tg-theme-text-color);
  margin-bottom: 10px;
`;

const Text = styled.p`
  color: var(--tg-theme-hint-color);
  margin: 5px 0;
`;

const Button = styled.button`
  margin-top: 15px;
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: none;
  background: var(--tg-theme-button-color);
  color: var(--tg-theme-button-text-color);
  cursor: pointer;
  transition: opacity 0.2s ease;

  &:hover {
    opacity: 0.8;
  }
`;

export function UserDashboard() {
  const userAddress = useTonAddress();
  const [countdown, setCountdown] = useState(6);
  const [showCloseButton, setShowCloseButton] = useState(false);
  const { t } = useLanguage();

  useEffect(() => {
    if (!userAddress) return;

    console.log('Validation successful, starting countdown...');
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setShowCloseButton(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [userAddress]);

  const handleClose = () => {
    window.Telegram.WebApp.close();
  };

  return (
    <Card>
      <Title>{t('dashboard.title')}</Title>
      <Text>{t('dashboard.wallet_confirmed')}</Text>
      {countdown > 0 ? (
        <Text>{t('dashboard.return_countdown').replace('{seconds}', countdown.toString())}</Text>
      ) : showCloseButton ? (
        <Button onClick={handleClose}>{t('dashboard.close')}</Button>
      ) : null}
    </Card>
  );
} 