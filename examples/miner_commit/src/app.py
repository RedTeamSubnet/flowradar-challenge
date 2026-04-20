import sys
import logging
import pathlib
from pathlib import Path

from fastapi import FastAPI, Body, HTTPException
from data_types import MinerInput, MinerOutput, CommitFilePM

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S %z",
    format="[%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d]: %(message)s",
)


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/solve", response_model=MinerOutput)
def solve(miner_input: MinerInput = Body(...)) -> MinerOutput:

    logger.info("Retrieving commit files...")
    _miner_output: MinerOutput
    try:
        _src_dir = pathlib.Path(__file__).parent.resolve()
        _commit_dir = _src_dir / "commit"
        _commit_paths: list[Path] = list(_commit_dir.glob("*.js"))

        _commit_files: list[CommitFilePM] = []
        for _commit_path in _commit_paths:
            with open(_commit_path) as _commit_file:
                _commit_file_pm = CommitFilePM(
                    file_name=_commit_path.name, content=_commit_file.read()
                )
                _commit_files.append(_commit_file_pm)

        _miner_output = MinerOutput(commit_files=_commit_files)
        logger.info("Successfully retrieved commit files.")
    except Exception as err:
        logger.error(f"Failed to retrieve commit files: {str(err)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve commit files.")

    return _miner_output


__all__ = ["app"]
