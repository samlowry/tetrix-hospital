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

export function UserDashboard() {
  const userAddress = useTonAddress();
  const [isRegistered, setIsRegistered] = React.useState<boolean>(false);

  React.useEffect(() => {
    async function verifyWallet() {
      if (!userAddress) return;

      try {
        console.log('Verifying wallet connection for:', userAddress);
        
        // Get TON Proof
        const { payload } = await api.getChallenge();
        const proof = await window.ton?.sendTonProof({ payload });
        if (!proof) {
          throw new Error('Failed to get TON Proof');
        }
        
        // Verify proof and register
        const { token } = await api.connectWallet({
          address: userAddress,
          proof
        });

        if (token) {
          console.log('Wallet verified successfully');
          setIsRegistered(true);
          // Close WebApp after 6 seconds
          setTimeout(() => {
            console.log('Closing WebApp...');
            window.Telegram.WebApp.close();
          }, 6000);
        }
      } catch (error) {
        console.error('Error in verification process:', error);
      }
    }

    verifyWallet();
  }, [userAddress]);

  return (
    <>
      <Card>
        <Title>User Status</Title>
        <Text>{isRegistered ? 'Registered Successfully' : 'Wallet Connected Successfully'}</Text>
      </Card>

      <Card>
        <Title>Next Steps</Title>
        <Text>Please use the Telegram bot to continue...</Text>
      </Card>
    </>
  );
} 