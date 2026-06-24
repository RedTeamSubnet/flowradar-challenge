# Do and Don't

## Do

- use multiple network signals (duration, packet lengths, packet counts, IAT, flags) instead of a single trigger.
- normalize inputs aggressively (safe casting, missing/null fallback, zero-division guards).
- train from the provided `v2_train_data.csv` and use `vpn_is_enabled` as label.
- keep the generated model JSON compact, valid, and deterministic.
- keep training in `train.py` and inference in `submissions.py`.
- tune for both precision and recall to improve F1, not only one side.
- keep runtime predictable and lightweight to avoid request misses/timeouts.
- iterate with score feedback and telemetry/logs after each meaningful change.

## Don't

- do not rely on one brittle threshold as the only VPN indicator.
- do not replace mandatory v2 training with `v1_train_data.csv`.
- do not expect `vpn_is_enabled` inside inference features; scoring removes it.
- do not assume optional values are always present or non-null.
- do not overfit to a tiny subset of rows or one traffic pattern.
- do not ignore false positives; over-flagging normal traffic hurts F1.
- do not ignore false negatives; under-detecting VPN traffic also hurts F1.
- do not throw exceptions on malformed input; return a safe prediction path.
- do not change production-parity scoring env values for final validation (`FLR_CHALLENGE_ACCEPTABLE_MISS_COUNT`, `FLR_CHALLENGE_SINGLE_REQUEST_TIMEOUT`).
