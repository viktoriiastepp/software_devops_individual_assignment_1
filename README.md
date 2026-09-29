# Padel Matchmaker

A web app for a padel club that handles court bookings and forms balanced matches between players of similar level.

## The problem
At a busy club (6 courts, around 400 members of mixed levels), players struggle to find three others at a similar level. Courts sit empty, or matches end up one-sided and nobody enjoys them.

## Stakeholders
- The club manager, who wants courts used efficiently and no double-bookings
- Club members, who want fair, competitive games without organising them over group chats

## Feature domains
1. **Court Bookings**: courts, opening hours and 90-minute slots. Rejects overlapping bookings and bookings outside opening hours, and flags late cancellations (less than 24 hours before).
2. **Matchmaking & Ratings**: players join open games only if their rating is within the game's level window. The app splits four players into the two most balanced teams and updates each player's rating after a result using an Elo-style formula.

## Status
In progress. Project changed from DepositGuard to Padel Matchmaker after professor feedback. Setup, run and test instructions will be added as the app is built.
