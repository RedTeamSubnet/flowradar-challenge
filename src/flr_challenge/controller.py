import os
import json

import requests

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
        miners_docker_info: dict[str, dict],
        seed_inputs: list[dict] = [],
    ):

        super().__init__(
            challenge_name,
            challenge_info,
            miner_commits,
            reference_comparison_commits,
            miners_docker_info,
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
        _higest_comparison_score = miner_commit.get_higest_comparison_score()
        if (
            _higest_comparison_score >= self.comparison_min_acceptable_score
            or _higest_comparison_score == 0.0
        ):
            bt.logging.info(
                f"[CONTROLLER - FLRController] Skipping scoring for miner {miner_commit.miner_hotkey} on task "
                f"due to high comparison score: {_higest_comparison_score}"
            )
            _scoring_log.score = 0.0
            if _scoring_log.error:
                _scoring_log.error += " | Skipped scoring due to high comparison score."
            else:
                _scoring_log.error = "Skipped scoring due to high comparison score."
            return

        score = (
            self._score_challenge(
                miner_input=challenge_inputs[0],
                miner_output=_scoring_log.miner_output,
                task_id=0,
            )
            if _scoring_log.miner_output is not None
            else 0.0
        )

        _scoring_log.score = score
        _payload, _feedback = self._get_results_from_challenge()
        _scoring_log.miner_output["scoring_results"] = _feedback
        self._save_result_to_data_folder(
            result_payload=_payload, docker_hub_id=miner_commit.docker_hub_id
        )
        _scoring_log.miner_output["telemetry"] = self._get_telemetry_from_challenge()
        return

    def _get_results_from_challenge(self) -> tuple[dict, dict]:
        result_url = "http://localhost:10001/results"
        try:
            response = requests.get(result_url, timeout=5, verify=False)  # nosec
            response.raise_for_status()
            _result_response = response.json() if response.content else {}
            _payload = _result_response.get("payload", {})
            _feedback = _result_response.get("feedback", {})
            return _payload, _feedback
        except Exception as exc:
            bt.logging.error(
                f"[CONTROLLER] Unable to fetch result from challenge endpoint: {exc}"
            )
            return {}, {}

    def _get_telemetry_from_challenge(self) -> dict:
        telemetry_url = "http://localhost:10001/telemetry"
        try:
            response = requests.get(telemetry_url, timeout=5, verify=False)  # nosec
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as exc:
            bt.logging.error(
                f"[CONTROLLER] Unable to fetch telemetry from challenge endpoint: {exc}"
            )
            return {}

    def _save_result_to_data_folder(
        self, result_payload: dict, docker_hub_id: str
    ) -> None:
        hfp_data_folder = os.environ.get("HFP_CHALLENGE_API_DATA_DIR")
        if not hfp_data_folder:
            bt.logging.warning(
                "[CONTROLLER] HFP_CHALLENGE_API_DATA_DIR environment variable not set, skipping result save"
            )
            return
        os.makedirs(hfp_data_folder, exist_ok=True)
        _docker_hub_id = docker_hub_id.split("/")[-1]
        result_file_path = os.path.join(
            hfp_data_folder, f"{_docker_hub_id}_result.json"
        )
        with open(result_file_path, "w") as f:
            f.write(json.dumps(result_payload, indent=4))
        bt.logging.info(f"[CONTROLLER] Result saved to {result_file_path}")

    def _exclude_output_keys(self, miner_output: dict, reference_output: dict) -> None:
        miner_output["commit_files"] = None
        reference_output["commit_files"] = None
        miner_output["telemetry"] = None
        reference_output["telemetry"] = None
        miner_output["scoring_results"] = None
        reference_output["scoring_results"] = None


__all__ = [
    "FLRController",
]
