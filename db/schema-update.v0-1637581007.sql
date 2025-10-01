-- -----------------------------------------------------
-- Update to Table `user`
-- -----------------------------------------------------

ALTER TABLE `user`
  ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255);
