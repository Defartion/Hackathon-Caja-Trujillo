\getenv fineract_user FINERACT_DB_USER
\getenv fineract_password FINERACT_DB_PASSWORD

CREATE ROLE :"fineract_user" LOGIN PASSWORD :'fineract_password';
CREATE DATABASE fineract_tenants OWNER :"fineract_user";
CREATE DATABASE fineract_default OWNER :"fineract_user";
