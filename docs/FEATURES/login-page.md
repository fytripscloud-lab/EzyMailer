# Feature: Login Page

## Goal

Provide a Windows desktop login screen for the first design milestone.

## Behavior

- Show username and password inputs
- Use `admin` as the username
- Use `admin` as the password
- On success, open the dashboard shell
- On failure, show a validation message

## Notes

- Login is backed by the backend API and the dedicated AWS MySQL `user_db` table
- The app seeds an initial `admin / admin` user for development and live bootstrap
