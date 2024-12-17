import React from 'react';
import styled from 'styled-components';
import { useTonAddress } from '@tonconnect/ui-react';
import { api } from '../api';

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

const HighlightText = styled.p`
  color: var(--tg-theme-accent-text-color);
  margin: 5px 0;
  font-weight: bold;
`;

export function UserDashboard() {
  const userAddress = useTonAddress();
  const [isFirstBacker, setIsFirstBacker] = React.useState<boolean>(false);
  const [isRegistered, setIsRegistered] = React.useState<boolean>(false);

  React.useEffect(() => {
    async function checkAndRegister() {
      if (!userAddress) return;

      try {
        console.log('Checking first backer status for:', userAddress);
        const { isFirstBacker } = await api.checkFirstBacker(userAddress);
        console.log('First backer status:', isFirstBacker);
        setIsFirstBacker(isFirstBacker);

        if (isFirstBacker) {
          console.log('Attempting to register early backer...');
          const messageId = window.Telegram.WebApp.initDataUnsafe?.start_param;
          console.log('Message ID from start_param:', messageId);
          
          // Get TON Proof
          const { payload } = await api.getChallenge();
          const proof = await window.ton?.sendTonProof({ payload });
          if (!proof) {
            throw new Error('Failed to get TON Proof');
          }
          
          const { success } = await api.registerEarlyBacker(userAddress, proof, messageId);
          console.log('Registration result:', success);
          if (success) {
            setIsRegistered(true);
            console.log('Registration successful, closing WebApp in 6 seconds...');
            // Close WebApp after 6 seconds
            setTimeout(() => {
              console.log('Closing WebApp...');
              window.Telegram.WebApp.close();
            }, 6000);
          }
        }
      } catch (error) {
        console.error('Error in registration process:', error);
      }
    }

    checkAndRegister();
  }, [userAddress]);

  return (
    <>
      <Card>
        <Title>User Status</Title>
        <Text>{isRegistered ? 'Registered Successfully' : 'Wallet Connected Successfully'}</Text>
        {isFirstBacker && (
          <HighlightText>🌟 Congratulations! You are among our first backers!</HighlightText>
        )}
      </Card>

      <Card>
        <Title>Next Steps</Title>
        <Text>Please use the Telegram bot to continue...</Text>
      </Card>
    </>
  );
} 