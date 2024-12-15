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

  interface Account {
    address: string;
  }

  export const useConnector: () => {
    connected: boolean;
    account: Account | null;
    connector: TonConnector;
  };
} 