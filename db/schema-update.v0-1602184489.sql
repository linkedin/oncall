-- -----------------------------------------------------
-- Update to Table `team`
-- -----------------------------------------------------

ALTER TABLE `team`
  ADD COLUMN IF NOT EXISTS slack_channel_notifications VARCHAR(255);
