import bittensor as bt

from redteam_core.challenge_pool.controller import Controller
from redteam_core.validator.models import MinerChallengeCommit


class FLRController(Controller):

    def __init__(
        self,
        challenge_name: str,
        challenge_info: dict,
        miner_commits: list[MinerChallengeCommit],
        reference_comparison_commits: list[MinerChallengeCommit],
        seed_inputs: list[dict] = [],
    ):

        super().__init__(
            challenge_name,
            challenge_info,
            miner_commits,
            reference_comparison_commits,
            seed_inputs,
        )
        comparison_config = self.challenge_info.get("comparison_config", {})
        self.comparison_min_acceptable_score = comparison_config.get(
            "min_acceptable_score", 0.6
        )

    def _score_miner_with_new_inputs(
        self, miner_commit: MinerChallengeCommit, challenge_inputs
    ) -> None:
        _scoring_log = miner_commit.scoring_logs[0]
        for i, miner_input in enumerate(challenge_inputs):

            _higest_comparison_score = miner_commit.get_higest_comparison_score()
            if (
                _higest_comparison_score >= self.comparison_min_acceptable_score
                or _higest_comparison_score == 0.0
            ):
                bt.logging.info(
                    f"[CONTROLLER - FLRController] Skipping scoring for miner {miner_commit.miner_hotkey} on task {i} "
                    f"due to high comparison score: {_higest_comparison_score}"
                )
                _scoring_log.score = 0.0
                if _scoring_log.error:
                    _scoring_log.error += (
                        " | Skipped scoring due to high comparison score."
                    )
                else:
                    _scoring_log.error = "Skipped scoring due to high comparison score."
                continue

            score = (
                self._score_challenge(
                    miner_input=miner_input,
                    miner_output=_scoring_log.miner_output,
                    task_id=i,
                )
                if _scoring_log.miner_output is not None
                else 0.0
            )

            _scoring_log.score = score

        return

    def _exclude_output_keys(self, miner_output: dict, reference_output: dict) -> None:
        return


__all__ = [
    "FLRController",
]
