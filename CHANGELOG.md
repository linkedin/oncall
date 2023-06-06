# Change Log
All notable changes to this project will be documented in this file.


## [2.0.0] - 2023-06-06
WARNING: this version adds a change to the MYSQL schema! Make changes to the schema before deploying new 2.0.0 version.

### Added
 - MINOR added the ability to designate teams as "api managed" which will prevent changes to team info from being done via the UI
### Changed
 - MAJOR added the `api_managed_roster` column to the `team` table in the MYSQL schema. Before running 2.0.0 the MYSQL schema must be updated with the command "ALTER TABLE team ADD api_managed_roster BOOLEAN NOT NULL DEFAULT FALSE;" to prevent an exception from being thrown from the GET /api/v0/teams/{team} endpoint
### Fixed
