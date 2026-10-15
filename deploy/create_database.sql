-- Execute only after inspecting and backing up the existing MySQL instance.
-- Creates the requested application database; does not drop or reset anything.
CREATE DATABASE IF NOT EXISTS chinese_study
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Create a dedicated application user using a secure administration console.
-- Grant only on chinese_study.*: SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES.
-- Never grant the application global privileges or use the MySQL root account.
