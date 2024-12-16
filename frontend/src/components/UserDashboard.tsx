import React from 'react';
import styled from 'styled-components';
import { useTonAddress } from '@tonconnect/ui-react';

const DashboardContainer = styled.div`
  padding: 20px;
  background: #1c1c1c;
  border-radius: 12px;
  margin: 20px 0;
  color: #ffffff;
`;

const InfoBlock = styled.div`
  margin-bottom: 15px;
  padding: 15px;
  background: #2a2a2a;
  border-radius: 8px;
`;

const Title = styled.h3`
  color: #ffffff;
  margin-bottom: 10px;
`;

const Text = styled.p`
  color: #b3b3b3;
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
      // Check if user is among first backers
      fetch('/user/check_first_backer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ address: userAddress }),
      })
        .then(response => response.json())
        .then(data => {
          setIsFirstBacker(data.isFirstBacker);
        })
        .catch(error => {
          console.error('Error checking first backer status:', error);
        });
    }
  }, [userAddress]);

  return (
    <DashboardContainer>
      <InfoBlock>
        <Title>Wallet Status</Title>
        <Text>Wallet Connected Successfully</Text>
        <Text>{userAddress}</Text>
        {isFirstBacker && (
          <HighlightText>🌟 Congratulations! You are among our first backers!</HighlightText>
        )}
      </InfoBlock>

      <InfoBlock>
        <Title>Next Steps</Title>
        <Text>Please use the Telegram bot to register your wallet and start earning TETRIX tokens.</Text>
      </InfoBlock>
    </DashboardContainer>
  );
} 