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
  const [isRegistered, setIsRegistered] = React.useState<boolean>(false);

  React.useEffect(() => {
    // Registration is now handled by the backend during proof verification
    // Just show the success message and let the app close automatically
    if (userAddress) {
      setIsRegistered(true);
    }
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