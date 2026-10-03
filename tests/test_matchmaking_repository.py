from matchmaking import repository as repo


def test_same_user_always_gets_the_same_player(temp_db):
    first = repo.get_or_create_player(user_id=1, name="Ana")
    second = repo.get_or_create_player(user_id=1, name="Ana")
    assert first["id"] == second["id"]
    assert first["rating"] == 1000


def test_full_game_flow_saves_teams_and_new_ratings(temp_db):
    game_id = repo.create_game(booking_id=42)
    ids = [repo.get_or_create_player(user_id=i, name=f"Player {i}")["id"] for i in range(1, 5)]
    for player_id in ids:
        repo.add_player_to_game(game_id, player_id)
    assert len(repo.players_in_game(game_id)) == 4

    repo.assign_teams(game_id, ids[:2], ids[2:])
    assert repo.get_game(game_id)["status"] == "full"

    repo.record_result(game_id, 1, {ids[0]: 1016, ids[1]: 1016, ids[2]: 984, ids[3]: 984})
    game = repo.get_game(game_id)
    assert game["status"] == "finished"
    assert game["winning_team"] == 1
    assert repo.leaderboard()[0]["rating"] == 1016


def test_open_games_list_skips_full_games(temp_db):
    open_id = repo.create_game(booking_id=1)
    full_id = repo.create_game(booking_id=2)
    repo.assign_teams(full_id, [], [])
    open_ids = [game["id"] for game in repo.list_games_by_status("open")]
    assert open_ids == [open_id]


def test_find_game_by_booking_and_games_of_a_player(temp_db):
    game_id = repo.create_game(booking_id=5)
    player = repo.get_or_create_player(user_id=1, name="Ana")
    repo.add_player_to_game(game_id, player["id"])
    assert repo.game_for_booking(5)["id"] == game_id
    assert repo.game_for_booking(6) is None
    assert [g["id"] for g in repo.games_for_player(player["id"])] == [game_id]
