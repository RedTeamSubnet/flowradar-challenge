import csv
import json
import sys


def _is_vpn(row):
    value = row.get("vpn_is_enabled", row.get("is_vpn", ""))
    return str(value).strip().lower() in {"true", "1", "yes"}


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main():
    train_csv = sys.argv[1]
    model_json = sys.argv[2]

    vpn_ratio_total = 0.0
    clean_ratio_total = 0.0
    vpn_count = 0
    clean_count = 0

    with open(train_csv, newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            fwd_bytes = _to_float(row.get("fwd_sum_pkt_len"))
            bwd_bytes = _to_float(row.get("bwd_sum_pkt_len"))
            ratio = bwd_bytes / fwd_bytes if fwd_bytes > 0 else bwd_bytes
            if _is_vpn(row):
                vpn_ratio_total += ratio
                vpn_count += 1
            else:
                clean_ratio_total += ratio
                clean_count += 1

    vpn_mean = vpn_ratio_total / max(1, vpn_count)
    clean_mean = clean_ratio_total / max(1, clean_count)
    model = {
        "version": 1,
        "ratio_threshold": (vpn_mean + clean_mean) / 2.0,
        "vpn_count": vpn_count,
        "clean_count": clean_count,
    }
    with open(model_json, "w", encoding="utf-8") as model_file:
        json.dump(model, model_file, separators=(",", ":"))


if __name__ == "__main__":
    main()
