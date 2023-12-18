# Steps we need:

# HAPPY FLOW
# -----------
# Game gets added to matches and results. The submit button on the Add Game page also triggers calculating ELO scores.
# For every player, calculate new elo
# For the two attackers, calculate new att elo
# For the two defenders, calculate new def elo
#
#
# ELO CALCULATION
# ---------------
# 1) Get latest rating from table (for each player)
# 2) Calculate expected score against opponents (for each player)
# 3) Calculate expected score for team (for each team)
# 4) Calculate point factor (once)
# 5) Calculate K factor (for each player)
# 6) Calculate new ELO rating (for each player)
# 7) Add rating to table

#
# DO NOT FORGET
# -------------
# When a new player registers, add a record for this player in the 3 ratings tables, with the default rating.
# Functionality for recalculating ELO scores over all (accepted) games
