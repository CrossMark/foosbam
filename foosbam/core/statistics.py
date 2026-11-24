from collections import defaultdict

from foosbam import db
from foosbam.models import Match, Result, User
import sqlalchemy as sa


def get_player_roles(user_id):
    roles = {'attacker': {'wins': 0, 'matches': 0}, 'defender': {'wins': 0, 'matches': 0}}
    matches = (
        db.session.query(Match, Result)
        .join(Result, Result.match_id == Match.id)
        .filter(sa.or_(
            Match.att_black == user_id, Match.def_black == user_id,
            Match.att_white == user_id, Match.def_white == user_id,
        ))
    )
    for match, result in matches:
        for role, player, won in (
            ('attacker', match.att_black, result.score_black > result.score_white),
            ('defender', match.def_black, result.score_black > result.score_white),
            ('attacker', match.att_white, result.score_white > result.score_black),
            ('defender', match.def_white, result.score_white > result.score_black),
        ):
            if player == user_id:
                roles[role]['matches'] += 1
                roles[role]['wins'] += won
    return roles


def get_leaderboards(searches):
    names = {user.id: user.username.title() for user in db.session.query(User).all()}
    rivalries = defaultdict(lambda: [0, 0])
    partnerships = defaultdict(lambda: [0, 0])
    roles = {'attacker': defaultdict(lambda: [0, 0]), 'defender': defaultdict(lambda: [0, 0])}
    keeper_goals = defaultdict(int)
    klinkers = defaultdict(int)

    matches = db.session.query(Match, Result).join(Result, Result.match_id == Match.id)
    for match, result in matches:
        teams = (
            (match.att_black, match.def_black, result.score_black, result.score_white,
             result.klinker_att_black, result.klinker_def_black, result.keeper_black),
            (match.att_white, match.def_white, result.score_white, result.score_black,
             result.klinker_att_white, result.klinker_def_white, result.keeper_white),
        )
        for team, opponents in ((teams[0], teams[1]), (teams[1], teams[0])):
            attacker, defender, score, opposing_score, att_klinkers, def_klinkers, keeper = team
            won = score > opposing_score
            partnership = partnerships[tuple(sorted((attacker, defender)))]
            partnership[0] += won
            partnership[1] += 1
            for role, player in (('attacker', attacker), ('defender', defender)):
                roles[role][player][0] += won
                roles[role][player][1] += 1
                for opponent in opponents[:2]:
                    rivalries[player, opponent][0] += won
                    rivalries[player, opponent][1] += 1
            klinkers[attacker] += att_klinkers
            klinkers[defender] += def_klinkers
            keeper_goals[defender] += keeper

    def player(player_id):
        return {'id': player_id, 'name': names[player_id]}

    def ranked(rows, key, search, search_both=False):
        search = search.casefold()
        rows = [
            row for row in rows
            if search in row['players'][0]['name'].casefold()
            or (search_both and search in row['players'][1]['name'].casefold())
        ]
        return sorted(rows, key=key)

    rivalry_rows = [
        {'players': [player(p), player(opponent)], 'wins': wins, 'matches': matches}
        for (p, opponent), (wins, matches) in rivalries.items()
    ]
    partnership_rows = [
        {'players': [player(p) for p in pair], 'wins': wins, 'matches': matches}
        for pair, (wins, matches) in partnerships.items()
    ]
    role_rows = {
        role: [
            {'players': [player(p)], 'wins': wins, 'matches': matches}
            for p, (wins, matches) in values.items()
        ]
        for role, values in roles.items()
    }
    count_rows = {
        'keeper': [{'players': [player(p)], 'total': total} for p, total in keeper_goals.items()],
        'klinker': [{'players': [player(p)], 'total': total} for p, total in klinkers.items()],
    }

    def names_key(row):
        return tuple(p['name'].casefold() for p in row['players'])

    def percentage_key(row):
        return (-row['wins'] / row['matches'], -row['matches'], names_key(row))

    return {
        'rivalry': ranked(
            rivalry_rows, lambda row: (-row['wins'], -row['matches'], names_key(row)),
            searches['rivalry'],
        ),
        'partnership': ranked(partnership_rows, percentage_key, searches['partnership'], True),
        **{
            role: ranked(rows, percentage_key, searches[role])
            for role, rows in role_rows.items()
        },
        **{
            category: ranked(rows, lambda row: (-row['total'], names_key(row)), searches[category])
            for category, rows in count_rows.items()
        },
    }
