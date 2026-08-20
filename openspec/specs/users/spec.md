# users Specification

## Purpose

Stores the user identity records that own todos and authenticate to the API. Each user has a unique email and a record-creation timestamp.

## Requirements

### Requirement: User record fields
The system SHALL persist each user with the fields defined in §3.1 of the TDD: `id` (UUID, primary key), `name` (varchar, up to 100 characters), `email` (varchar, up to 150 characters, unique across all users), and `created_at` (timestamp set at creation).

#### Scenario: User record is created with all required fields
- **WHEN** a user is registered
- **THEN** the system persists `id` (a generated UUID), `name`, `email`, and `created_at` (server time at creation)

#### Scenario: Email is unique across users
- **WHEN** two registrations attempt to use the same `email`
- **THEN** the second registration MUST be rejected and MUST NOT create a duplicate user

### Requirement: Unique email index
The system SHALL maintain a unique index on `users.email` as defined in §8 of the TDD.

#### Scenario: Unique index prevents duplicate email
- **WHEN** the database is migrated
- **THEN** a unique index exists on `users.email` and any attempt to insert a duplicate email fails at the database layer
