ALTER TABLE "user" ADD COLUMN password_hash VARCHAR(60);
ALTER TABLE "user" ADD COLUMN refresh_token VARCHAR(1024);
ALTER TABLE "user" ALTER COLUMN avatar DROP NOT null;
