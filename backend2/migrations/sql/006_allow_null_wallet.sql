-- UP
ALTER TABLE "user" ALTER COLUMN wallet_address DROP NOT NULL;
ALTER TABLE "user" DROP CONSTRAINT check_wallet_address;
ALTER TABLE "user" ADD CONSTRAINT check_wallet_address CHECK (wallet_address IS NULL OR wallet_address ~ '^0:[a-fA-F0-9]{64}$');

-- DOWN
ALTER TABLE "user" DROP CONSTRAINT check_wallet_address;
ALTER TABLE "user" ADD CONSTRAINT check_wallet_address CHECK (wallet_address ~ '^0:[a-fA-F0-9]{64}$');
ALTER TABLE "user" ALTER COLUMN wallet_address SET NOT NULL; 