declare module '@tonconnect/ui-react' {
  export interface TonConnectButtonProps {
    className?: string;
  }
  export const TonConnectButton: React.FC<TonConnectButtonProps>;
  export interface TonConnectUIProviderProps {
    manifestUrl: string;
    children: React.ReactNode;
    walletsList?: {
      includeWallets?: string[];
      excludeWallets?: string[];
    };
  }
  export const TonConnectUIProvider: React.FC<TonConnectUIProviderProps>;

  interface TonConnector {
    signMessage: (params: { message: string }) => Promise<string>;
  }

  export const useTonConnect: () => {
    wallet: {
      account: {
        address: string;
      };
    } | null;
    connector: TonConnector;
  };
} 