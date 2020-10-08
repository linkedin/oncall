-- Sample MySQL data. Can be loaded after initializing schema

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES
    (1,'root',1,'God User',NULL,NULL,1),
    (2,'manager',1,'Team Admin',NULL,NULL,0),
    (3,'jdoe',1,'Juan Doş',NULL,NULL,0),
    (4,'asmith',1,'Alice Smith',NULL,NULL,0);
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `team` WRITE;
/*!40000 ALTER TABLE `team` DISABLE KEYS */;
INSERT INTO `team` VALUES (1,'Test Team','#team','#team-alerts','team@example.com','US/Pacific',1,NULL,0,NULL);
/*!40000 ALTER TABLE `team` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `service` WRITE;
/*!40000 ALTER TABLE `service` DISABLE KEYS */;
INSERT INTO `service` VALUES (1,'test service');
/*!40000 ALTER TABLE `service` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `notification_setting` WRITE;
/*!40000 ALTER TABLE `notification_setting` DISABLE KEYS */;
INSERT INTO `notification_setting` VALUES
    (1,4,1,1,1,86400,NULL),
    (2,4,1,1,1,604800,NULL),
    (3,2,1,1,1,86400,NULL),
    (4,2,1,1,1,604800,NULL),
    (7,3,1,1,1,86400,NULL),
    (8,3,1,1,1,604800,NULL),
    (9,4,1,1,3,NULL,1);
/*!40000 ALTER TABLE `notification_setting` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `roster` WRITE;
/*!40000 ALTER TABLE `roster` DISABLE KEYS */;
INSERT INTO `roster` VALUES (1,'Test Roster',1),(2,'Test Roster 2',1);
/*!40000 ALTER TABLE `roster` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `roster_user` WRITE;
/*!40000 ALTER TABLE `roster_user` DISABLE KEYS */;
INSERT INTO `roster_user` VALUES (1,3,1,0),(1,4,1,1),(2,2,1,0);
/*!40000 ALTER TABLE `roster_user` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `schedule` WRITE;
/*!40000 ALTER TABLE `schedule` DISABLE KEYS */;
INSERT INTO `schedule` VALUES (1,1,1,1,21,0,1496559600,NULL,1),(2,1,2,4,21,0,1496559600,NULL,1);
/*!40000 ALTER TABLE `schedule` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `schedule_event` WRITE;
/*!40000 ALTER TABLE `schedule_event` DISABLE KEYS */;
INSERT INTO `schedule_event` VALUES (1,1,205200,604800),(2,2,205200,604800);
/*!40000 ALTER TABLE `schedule_event` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `setting_role` WRITE;
/*!40000 ALTER TABLE `setting_role` DISABLE KEYS */;
INSERT INTO `setting_role` VALUES (1,1),(2,1),(3,1),(4,1),(7,1),(8,1),(9,1),(1,2),(2,2),(3,2),(4,2),(7,2),(8,2),(1,3),(2,3),(3,3),(4,3),(7,3),(8,3),(1,4),(2,4),(3,4),(4,4),(7,4),(8,4);
/*!40000 ALTER TABLE `setting_role` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `team_admin` WRITE;
/*!40000 ALTER TABLE `team_admin` DISABLE KEYS */;
INSERT INTO `team_admin` VALUES (1,2),(1,4);
/*!40000 ALTER TABLE `team_admin` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `team_service` WRITE;
/*!40000 ALTER TABLE `team_service` DISABLE KEYS */;
INSERT INTO `team_service` VALUES (1,1);
/*!40000 ALTER TABLE `team_service` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `team_user` WRITE;
/*!40000 ALTER TABLE `team_user` DISABLE KEYS */;
INSERT INTO `team_user` VALUES (1,2),(1,3),(1,4);
/*!40000 ALTER TABLE `team_user` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `user_contact` WRITE;
/*!40000 ALTER TABLE `user_contact` DISABLE KEYS */;
INSERT INTO `user_contact` VALUES
    (1,3,'+1 111-111-1111'),
    (1,4,'root'),
    (1,2,'+1 111-111-1111'),
    (1,1,'root@example.com'),

    (2,3,'+1 222-222-2222'),
    (2,4,'bsmith'),
    (2,2,'+1 222-222-2222'),
    (2,1,'bsmith@example.com'),

    (3,3,'+1 333-333-3333'),
    (3,4,'jdoe'),
    (3,2,'+1 333-333-3333'),
    (3,1,'jdoe@example.com'),

    (4,3,'+1 444-444-4444'),
    (4,4,'asmith'),
    (4,2,'+1 444-444-4444'),
    (4,1,'asmith@example.com');
/*!40000 ALTER TABLE `user_contact` ENABLE KEYS */;
UNLOCK TABLES;


LOCK TABLES `event` WRITE;
/*!40000 ALTER TABLE `event` DISABLE KEYS */;
INSERT INTO `event` (`id`, `team_id`, `role_id`, `schedule_id`, `user_id`, `start`, `end`) VALUES
    (1,1,1,1,3,1495555200,1496160000),
    (2,1,1,1,4,1496160000,1496764800),
    (3,1,1,1,3,1496764800,1497369600),
    (7,1,4,2,2,1495555200,1496160000),
    (8,1,4,2,2,1496160000,1496764800),
    (9,1,4,2,2,1496764800,1497369600);
/*!40000 ALTER TABLE `event` ENABLE KEYS */;
UNLOCK TABLES;

