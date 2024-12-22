import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useTonAddress } from '@tonconnect/ui-react';

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
`;

export function UserDashboard() {
  const userAddress = useTonAddress();
  const [countdown, setCountdown] = useState(6);
  const [showCloseButton, setShowCloseButton] = useState(false);

  useEffect(() => {
    async function handleValidation() {
      if (!userAddress) return;

      try {
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
      } catch (error) {
        console.error('Error:', error);
      }
    }

    handleValidation();
  }, [userAddress]);

  const handleClose = () => {
    window.Telegram.WebApp.close();
  };

  return (
    <Card>
      <Title>Статус проверки</Title>
      <Text>Кошелёк успешно подтверждён</Text>
      {countdown > 0 ? (
        <Text>Возвращаемся к боту через {countdown} сек...</Text>
      ) : showCloseButton ? (
        <Button onClick={handleClose}>Закрыть</Button>
      ) : null}
    </Card>
  );
} 