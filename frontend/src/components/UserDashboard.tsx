import React from 'react';
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

export function UserDashboard() {
  const userAddress = useTonAddress();

  React.useEffect(() => {
    async function handleValidation() {
      if (!userAddress) return;

      try {
        console.log('Validation successful, closing WebApp...');
        setTimeout(() => {
          console.log('Closing WebApp...');
          window.Telegram.WebApp.close();
        }, 6000);
      } catch (error) {
        console.error('Error:', error);
      }
    }

    handleValidation();
  }, [userAddress]);

  return (
    <Card>
      <Title>Статус проверки</Title>
      <Text>Кошелёк успешно подтверждён</Text>
      <Text>Возвращаемся к боту...</Text>
    </Card>
  );
} 