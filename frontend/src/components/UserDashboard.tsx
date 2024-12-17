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
    async function checkAndRegister() {
      if (!userAddress) return;

      try {
        console.log('Connection successful, closing WebApp in 6 seconds...');
        setTimeout(() => {
          console.log('Closing WebApp...');
          window.Telegram.WebApp.close();
        }, 6000);
      } catch (error) {
        console.error('Error:', error);
      }
    }

    checkAndRegister();
  }, [userAddress]);

  return (
    <Card>
      <Title>User Status</Title>
      <Text>Wallet Connected Successfully</Text>
      <Text>Please wait while we redirect you back to Telegram...</Text>
    </Card>
  );
} 