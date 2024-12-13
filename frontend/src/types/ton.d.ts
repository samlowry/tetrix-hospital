declare module '@tonconnect/ui-react' {
  export interface TonConnectButtonProps {
    // Add button props here
  }
  export const TonConnectButton: React.FC<TonConnectButtonProps>;
  export const useTonConnect: () => {
    wallet: {
      account: {
        address: string;
      };
    } | null;
  };
} 