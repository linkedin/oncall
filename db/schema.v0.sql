CREATE DATABASE IF NOT EXISTS `oncall` DEFAULT CHARACTER SET utf8 ;
USE `oncall`;

-- -----------------------------------------------------
-- Table `team`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `team` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `slack_channel` VARCHAR(255),
  `email` VARCHAR(255),
  `scheduling_timezone` VARCHAR(255),
  `active` BOOLEAN NOT NULL DEFAULT TRUE,
  `iris_plan` VARCHAR(255),
  `iris_enabled` BOOLEAN NOT NULL DEFAULT FALSE,
  `override_phone_number` VARCHAR(255),
  PRIMARY KEY (`id`),
  UNIQUE INDEX `name_unique` (`name` ASC));

-- -----------------------------------------------------
-- Table `deleted_team`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `deleted_team` (
  `team_id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `new_name` VARCHAR(255) NOT NULL,
  `old_name` VARCHAR(255) NOT NULL,
  `deletion_date` BIGINT(20) NOT NULL,
  PRIMARY KEY (`team_id`),
  CONSTRAINT `deleted_team_team_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  UNIQUE INDEX `new_name_unique` (`new_name` ASC));

-- -----------------------------------------------------
-- Table `user`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `user` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(45) NOT NULL,
  `active` BOOL DEFAULT 1 NOT NULL,
  `full_name` VARCHAR(255),
  `time_zone` VARCHAR(64),
  `photo_url` VARCHAR(255),
  `god` BOOL DEFAULT 0 NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `username_unique` (`name` ASC));

-- -----------------------------------------------------
-- Table `pinned_team`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `pinned_team` (
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  INDEX `team_member_team_id_idx` (`team_id` ASC),
  INDEX `team_member_user_id_idx` (`user_id` ASC),
  PRIMARY KEY (`team_id`, `user_id`),
  CONSTRAINT `pinned_team_team_id_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `pinned_team_user_id_fk`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE);

-- -----------------------------------------------------
-- Table `team_user`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `team_user` (
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  INDEX `team_member_team_id_idx` (`team_id` ASC),
  INDEX `team_member_user_id_idx` (`user_id` ASC),
  PRIMARY KEY (`team_id`, `user_id`),
  CONSTRAINT `team_user_team_id_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `team_user_user_id_fk`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION);

-- -----------------------------------------------------
-- Table `team_admin`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `team_admin` (
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  INDEX `team_member_team_id_idx` (`team_id` ASC),
  INDEX `team_member_user_id_idx` (`user_id` ASC),
  PRIMARY KEY (`team_id`, `user_id`),
  CONSTRAINT `team_admin_team_id_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `team_admin_user_id_fk`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION);

-- -----------------------------------------------------
-- Table `roster`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `roster` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `roster_team_id_fk_idx` (`team_id` ASC),
  UNIQUE INDEX `roster_team_id_name_unique` (`name` ASC, `team_id` ASC),
  CONSTRAINT `roster_team_id_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE);

-- -----------------------------------------------------
-- Table `role`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `role` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(45) NOT NULL,
  `display_order` INT UNSIGNED NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `name_unique` (`name` ASC));

INSERT INTO `role` (`name`, `display_order`)
VALUES ('primary', 1),
       ('secondary', 2),
       ('shadow', 3),
       ('manager', 4),
       ('vacation', 5),
       ('unavailable', 6);

-- -----------------------------------------------------
-- Table `scheduler``
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `scheduler` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL UNIQUE,
  `description` TEXT NOT NULL,
  PRIMARY KEY (`id`)
);

-- -----------------------------------------------------
-- Table `schedule`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `schedule` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  `roster_id` BIGINT(20) UNSIGNED NOT NULL,
  `role_id` INT UNSIGNED NOT NULL,
  -- unit in days
  `auto_populate_threshold` INT UNSIGNED NOT NULL DEFAULT 0,
  -- 0: display schedule in "simple mode" (handoff time, rotation period)
  -- 1: display schedule in "advanced mode" (individual events)
  `advanced_mode` TINYINT(1) NOT NULL,
  `last_epoch_scheduled` BIGINT(20) UNSIGNED,
  `last_scheduled_user_id` BIGINT(20) UNSIGNED,
  `scheduler_id` INT(11) UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `schedule_roster_id_idx` (`roster_id` ASC),
  INDEX `schedule_role_id_idx` (`role_id` ASC),
  INDEX `schedule_team_id_idx` (`team_id` ASC),
  CONSTRAINT `schedule_roster_id_fk`
    FOREIGN KEY (`roster_id`)
    REFERENCES `roster` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION,
  CONSTRAINT `schedule_role_id_fk`
    FOREIGN KEY (`role_id`)
    REFERENCES `role` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `schedule_team_id_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `schedule_scheduler_id_fk`
    FOREIGN KEY (`scheduler_id`)
    REFERENCES `scheduler` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `schedule_last_user_id_fk`
    FOREIGN KEY (`last_scheduled_user_id`)
    REFERENCES `user` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION
);

-- -----------------------------------------------------
-- Table `schedule_event`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `schedule_event` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `schedule_id` BIGINT(20) UNSIGNED NOT NULL,
  -- seconds since Sunday 12 midnight ('schedule epoch')
  `start` BIGINT(20) NOT NULL,
  -- units of seconds
  `duration` BIGINT(20) NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `schedule_event_schedule_id_idx` (`schedule_id` ASC),
  CONSTRAINT `schedule_events_schedule_id_fk`
    FOREIGN KEY (`schedule_id`) REFERENCES `schedule`(`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

-- -----------------------------------------------------
-- Table `event`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `event` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  `role_id` INT UNSIGNED NOT NULL,
  `schedule_id` BIGINT(20) UNSIGNED,
  -- id for linked events
  `link_id` CHAR(32),
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  -- seconds since epoch (unix timestamp)
  `start` BIGINT(20) NOT NULL,
  `end` BIGINT(20) NOT NULL,
  `note` TEXT,
  PRIMARY KEY (`id`),
  INDEX `event_role_id_fk_idx` (`role_id` ASC),
  INDEX `event_user_id_fk_idx` (`user_id` ASC),
  INDEX `event_team_id_fk_idx` (`team_id` ASC),
  INDEX `event_link_id_idx` (`link_id` ASC),
  CONSTRAINT `event_user_id_fk`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `event_role_id_fk`
    FOREIGN KEY (`role_id`)
    REFERENCES `role` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `event_team_id_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE);

-- -----------------------------------------------------
-- Table `service`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `service` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `name_unique` (`name` ASC));

-- -----------------------------------------------------
-- Table `team_service`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `team_service` (
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  `service_id` BIGINT(20) UNSIGNED NOT NULL,
  PRIMARY KEY (`team_id`, `service_id`),
  INDEX `team_service_service_id_fk_idx` (`service_id` ASC),
  CONSTRAINT `team_service_team_id_fk`
    FOREIGN KEY (`team_id`)
    REFERENCES `team` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `team_service_service_id_fk`
    FOREIGN KEY (`service_id`)
    REFERENCES `service` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION);

-- -----------------------------------------------------
-- Table `roster_user`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `roster_user` (
  `roster_id` BIGINT(20) UNSIGNED NOT NULL,
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  `in_rotation` BOOLEAN NOT NULL DEFAULT 1,
  `roster_priority` INT(11) UNSIGNED NOT NULL,
  PRIMARY KEY (`roster_id`, `user_id`),
  INDEX `roster_user_user_id_fk_idx` (`user_id` ASC),
  CONSTRAINT `roster_user_user_id_fk`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `roster_user_roster_id_fk`
    FOREIGN KEY (`roster_id`)
    REFERENCES `roster` (`id`)
    ON DELETE CASCADE);

-- -----------------------------------------------------
-- Table `contact_mode`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `contact_mode` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
);
-- -----------------------------------------------------
-- Initialize contact modes
-- -----------------------------------------------------
INSERT INTO `contact_mode` (`name`)
VALUES ('email'), ('sms'), ('call'), ('slack'), ('teams_messenger');

-- -----------------------------------------------------
-- Table `user_contact`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_contact` (
  `user_id` bigint(20) unsigned NOT NULL,
  `mode_id` int(11) NOT NULL,
  `destination` varchar(255) NOT NULL,
  PRIMARY KEY (`user_id`,`mode_id`),
  KEY `ix_user_contact_mode_id` (`mode_id`),
  CONSTRAINT `user_contact_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `user_contact_mode_id_fk` FOREIGN KEY (`mode_id`) REFERENCES `contact_mode` (`id`)
    ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Table `audit`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `audit` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT,
  `owner_name` VARCHAR(255) NOT NULL,
  `team_name` VARCHAR(255) NOT NULL,
  `action_name` VARCHAR(255) NOT NULL,
  `context` TEXT NOT NULL,
  `timestamp` BIGINT(20) NOT NULL,
  PRIMARY KEY (`id`)
);

-- -----------------------------------------------------
-- Table `session`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `session` (
  `id` CHAR(40) NOT NULL,
  `csrf_token` CHAR(32) NOT NULL,
  `time_created` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
);

-- -----------------------------------------------------
-- Table `notification_type`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `notification_type` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `subject` TEXT NOT NULL,
  `body` TEXT NOT NULL,
  `is_reminder` BOOLEAN NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `name_unique` (`name` ASC)
);

-- -----------------------------------------------------
-- Table `notification_setting`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `notification_setting` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  `team_id` BIGINT(20) UNSIGNED NOT NULL,
  `mode_id` INT(11) NOT NULL,
  `type_id` BIGINT(20) UNSIGNED NOT NULL,
  `time_before` INT(11),
  `only_if_involved` BOOLEAN,
  PRIMARY KEY (`id`),
  CONSTRAINT `notification_setting_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `notification_setting_team_id_fk` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `notification_setting_mode_id_fk` FOREIGN KEY (`mode_id`) REFERENCES `contact_mode` (`id`),
  CONSTRAINT `notification_setting_type_id_fk` FOREIGN KEY (`type_id`) REFERENCES `notification_type` (`id`)
);

-- -----------------------------------------------------
-- Table `setting_role`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `setting_role` (
  `setting_id` BIGINT(20) UNSIGNED NOT NULL,
  `role_id` INT UNSIGNED NOT NULL,
  PRIMARY KEY(`setting_id`, `role_id`),
  CONSTRAINT `setting_role_setting_id_fk` FOREIGN KEY (`setting_id`) REFERENCES `notification_setting` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `setting_role_role_id_fk` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`)
    ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Table `notification_queue`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `notification_queue` (
  `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  `send_time` BIGINT(20) UNSIGNED NOT NULL,
  `mode_id` INT(11) NOT NULL,
  `context` TEXT NOT NULL,
  `type_id` BIGINT(20) UNSIGNED NOT NULL,
  `active` BOOL,
  `sent` BOOL,
  PRIMARY KEY (`id`),
  CONSTRAINT `notification_queue_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `notification_queue_type_id_fk` FOREIGN KEY (`type_id`) REFERENCES `notification_type` (`id`)
);

-- -----------------------------------------------------
-- Table `notifier_state`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `notifier_state` (
  `last_window_end` BIGINT(20) UNSIGNED NOT NULL,
  PRIMARY KEY (`last_window_end`)
);

-- -----------------------------------------------------
-- Table `application`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `application` (
  `id` INT(11) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` CHAR(255) NOT NULL,
  `key` varchar(64) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE IF NOT EXISTS `team_subscription` (
  `team_id`         BIGINT(20) UNSIGNED NOT NULL,
  `subscription_id` BIGINT(20) UNSIGNED NOT NULL,
  `role_id`         INT        UNSIGNED NOT NULL,
  PRIMARY KEY (`team_id`, `subscription_id`, `role_id`),
  INDEX `team_subscription_team_id_idx` (`team_id` ASC),
  CONSTRAINT `team_subscription_team_id_fk` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `team_subscription_subscription_id_fk` FOREIGN KEY (`subscription_id`) REFERENCES `team` (`id`)
    ON DELETE CASCADE,
  INDEX `team_subscription_team_id_fk_idx` (`team_id` ASC)
);

CREATE TABLE IF NOT EXISTS `schedule_order` (
  `schedule_id` BIGINT(20) UNSIGNED NOT NULL,
  `user_id` BIGINT(20) UNSIGNED NOT NULL,
  `priority` INT(11) UNSIGNED NOT NULL,
  PRIMARY KEY (`schedule_id`,`user_id`),
  CONSTRAINT `schedule_order_schedule_id_fk` FOREIGN KEY (`schedule_id`) REFERENCES `schedule` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `schedule_order_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON DELETE CASCADE,
  INDEX `schedule_order_schedule_id_idx` (`schedule_id`)
);

INSERT INTO `scheduler` ( `name`, `description`)
VALUES ('default',
        'Default scheduling algorithm'),
       ('round-robin',
        'Round robin in roster order; does not respect vacations/conflicts'),
  ('no-skip-matching',
   'Default scheduling algorithm; doesn\'t skips creating events if matching events already exist on the calendar');

-- -----------------------------------------------------
-- Initialize notification types
-- -----------------------------------------------------
INSERT INTO `notification_type` (`name`, `subject`, `body`, `is_reminder`)
VALUES ('oncall_reminder',
        'Reminder: oncall shift for %(team)s starts in %(time_before)s',
        'Your %(role)s shift for %(team)s starts at %(start_time)s',
        TRUE),
       ('offcall_reminder',
        'Reminder: oncall shift for %(team)s ends in %(time_before)s',
        'Your %(role)s shift for %(team)s ends at %(end_time)s',
        TRUE),
       ('event_created',
        'Notice: %(role)s on-call event created for %(full_name)s',
        'A %(role)s shift for %(full_name)s starting at %(start_time)s has been created on the %(team)s calendar',
        FALSE),
       ('event_edited',
        'Notice: %(role)s on-call event edited for %(full_name)s',
        'A %(role)s shift for %(full_name)s starting at %(start_time)s has been changed on the %(team)s calendar. New event info: %(new_event)s',
        FALSE),
       ('event_deleted',
        'Notice: %(role)s on-call event deleted for %(full_name)s',
        'A %(role)s shift for %(full_name)s starting at %(start_time)s has been deleted on the %(team)s calendar',
        FALSE),
       ('event_swapped',
        'Notice: On-call shifts swapped between %(full_name_0)s and %(full_name_1)s',
        '%(full_name_0)s\'s shift beginning at %(start_time_0)s was swapped with %(full_name_1)s\'s shift beginning at %(start_time_1)s on the %(team)s calendar.',
        FALSE),
       ('event_substituted',
        'Notice: %(full_name_0)s substituted in for %(full_name_1)s',
        '%(full_name_0)s took over %(full_name_1)s\'s %(role)s shift on the %(team)s calendar from %(start_time)s to %(end_time)s',
        FALSE);
