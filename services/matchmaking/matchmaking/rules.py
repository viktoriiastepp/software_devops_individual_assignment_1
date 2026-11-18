"""Business rules for matchmaking. No database code here, so everything is easy to test."""

PLAYERS_PER_GAME = 4
LEVEL_WINDOW = 150  # max rating distance from the game's average to be allowed to join
K_FACTOR = 32  # how much one match can move a rating (standard Elo value)


def team_rating(team):
    """Average rating of a team. A team is a list of (player_id, rating) pairs."""
    return sum(rating for _, rating in team) / len(team)


def validate_join(player_rating, current_ratings, already_joined=False):
    """Return a list of reasons the player cannot join. An empty list means they can."""
    errors = []
    if already_joined:
        errors.append("You have already joined this game.")
    if len(current_ratings) >= PLAYERS_PER_GAME:
        errors.append("This game is already full.")
    elif current_ratings:
        average = sum(current_ratings) / len(current_ratings)
        if abs(player_rating - average) > LEVEL_WINDOW:
            errors.append("Your rating is too far from this game's level.")
    return errors


def balanced_teams(players):
    """Split 4 players into the two teams with the closest average rating.

    With 4 players there are only 3 possible splits: the first player
    partners with each of the other three. We try all 3 and keep the best.
    """
    if len(players) != PLAYERS_PER_GAME:
        raise ValueError("A game needs exactly 4 players.")
    first = players[0]
    best = None
    for partner in players[1:]:
        team_1 = [first, partner]
        team_2 = [p for p in players if p not in team_1]
        difference = abs(team_rating(team_1) - team_rating(team_2))
        if best is None or difference < best[0]:
            best = (difference, team_1, team_2)
    return best[1], best[2]


def expected_score(rating, opponent_rating):
    """Elo: the chance (0 to 1) that a side with this rating beats the opponent."""
    return 1 / (1 + 10 ** ((opponent_rating - rating) / 400))


def rating_change(rating, opponent_rating, won):
    """How many points the side gains (positive) or loses (negative)."""
    actual = 1 if won else 0
    return round(K_FACTOR * (actual - expected_score(rating, opponent_rating)))


def new_ratings(team_1, team_2, team_1_won):
    """Return {player_id: new_rating} for all 4 players.

    Both players in a team get the same change, and team 2 loses exactly
    what team 1 gains, so the total of all ratings never changes.
    """
    change = rating_change(team_rating(team_1), team_rating(team_2), team_1_won)
    updated = {}
    for player_id, rating in team_1:
        updated[player_id] = rating + change
    for player_id, rating in team_2:
        updated[player_id] = rating - change
    return updated
