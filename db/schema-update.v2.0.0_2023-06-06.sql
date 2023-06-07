-- -----------------------------------------------------
-- Update to Table `team`
-- -----------------------------------------------------

ALTER TABLE `team`
  ADD `api_managed_roster` BOOLEAN NOT NULL DEFAULT FALSE;
