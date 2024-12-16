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
  color: #00ff00;
  margin: 5px 0;
  font-weight: bold;
`;

export function UserDashboard() {
  const userAddress = useTonAddress();
  const [isFirstBacker, setIsFirstBacker] = React.useState<boolean>(false);

  React.useEffect(() => {
    if (userAddress) {
      api.checkFirstBacker(userAddress)
        .then(data => {
          setIsFirstBacker(data.isFirstBacker);
        })
        .catch(error => {
          console.error('Error checking first backer status:', error);
        });
    }
  }, [userAddress]);

  return (
    <>
      <Card>
        <Text>{userAddress}</Text>
        <Title>Wallet Status</Title>
        <Text>Wallet Connected Successfully</Text>
        <Text>{userAddress}</Text>
        {isFirstBacker && (
          <HighlightText>🌟 Congratulations! You are among our first backers!</HighlightText>
        )}
      </Card>

      <Card>
        <Title>Next Steps</Title>
        <Text>Please use the Telegram bot to register your wallet and start earning TETRIX tokens.</Text>
      </Card>
    </>
  );
} 