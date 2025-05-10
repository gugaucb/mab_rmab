import os
from bandits.multi_armed_bandit import run as run_multi_armed_bandit
from bandits.rank_multi_armed_bandit import run as run_rank_multi_armed_bandit

BANDIT_MODE = os.getenv("BANDIT_MODE", "multi_armed_bandit")

if __name__ == "__main__":
    if BANDIT_MODE == "multi_armed_bandit":
        # Example usage of MultiArmedBandit
        bandit = run_multi_armed_bandit()
        bandit.run()
    elif BANDIT_MODE == "rank_multi_armed_bandit":
        # Example usage of RankMultiArmedBandit
        bandit = run_rank_multi_armed_bandit()
        bandit.run()
    else:
        print("Invalid BANDIT_MODE. Please choose 'multi_armed_bandit' or 'rank_multi_armed_bandit'.")
