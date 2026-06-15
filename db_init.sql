-- Create schema
CREATE SCHEMA IF NOT EXISTS moneyprinter;

-- Grant privileges on schema to the application user
GRANT ALL ON SCHEMA moneyprinter TO postgres;

-- Set search_path at the DB level
ALTER DATABASE moneyprinter SET search_path TO moneyprinter, public;
