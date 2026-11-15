import pytest

from matchmaking import rules


def test_anyone_can_join_an_empty_game():
    assert rules.validate_join(1000, []) == []


def test_player_within_level_window_can_join():
    assert rules.validate_join(1100, [1000, 1050]) == []


def test_player_exactly_at_window_edge_can_join():
    assert rules.validate_join(1150, [1000]) == []


def test_player_too_far_from_game_level_is_rejected():
    errors = rules.validate_join(1300, [1000, 1050])
    assert "Your rating is too far from this game's level." in errors


def test_full_game_is_rejected():
    errors = rules.validate_join(1000, [1000, 1000, 1000, 1000])
    assert "This game is already full." in errors


def test_player_cannot_join_twice():
    errors = rules.validate_join(1000, [1000], already_joined=True)
    assert "You have already joined this game." in errors


def test_balanced_teams_picks_the_closest_split():
    players = [(1, 1200), (2, 1000), (3, 1100), (4, 900)]
    team_1, team_2 = rules.balanced_teams(players)
    assert team_1 == [(1, 1200), (4, 900)]
    assert team_2 == [(2, 1000), (3, 1100)]


def test_balanced_teams_needs_exactly_four_players():
    with pytest.raises(ValueError):
        rules.balanced_teams([(1, 1000), (2, 1000), (3, 1000)])


def test_equal_teams_have_even_chances():
    assert rules.expected_score(1000, 1000) == 0.5


def test_beating_an_equal_team_gives_16_points():
    assert rules.rating_change(1000, 1000, won=True) == 16


def test_upset_win_gives_more_points_than_expected_win():
    assert rules.rating_change(900, 1100, won=True) > 16


def test_new_ratings_for_equal_teams():
    updated = rules.new_ratings([(1, 1000), (2, 1000)], [(3, 1000), (4, 1000)], team_1_won=True)
    assert updated == {1: 1016, 2: 1016, 3: 984, 4: 984}


def test_total_rating_stays_the_same_after_a_match():
    team_1 = [(1, 1200), (2, 900)]
    team_2 = [(3, 1000), (4, 1100)]
    updated = rules.new_ratings(team_1, team_2, team_1_won=False)
    assert sum(updated.values()) == 1200 + 900 + 1000 + 1100
