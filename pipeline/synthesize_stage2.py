"""Stage 2 roll-up: read each per-stock bull/bear/synthesis note and rank by conviction.

Each note must end its synthesis with `Conviction: NN/100` and `Advance: yes|no`; a note
missing either is an error, not a silent default.
"""
from __future__ import annotations

import os
import re
import sys

import pandas as pd


def main(run_dir: str, extra_csv: str | None = None) -> None:
    d = os.path.join(run_dir, "stage2_adversarial")
    top = pd.read_csv(os.path.join(run_dir, "stage1_screen", "top_30.csv"))
    meta = pd.read_csv(extra_csv).set_index("symbol") if extra_csv else None
    rows = []
    for sym in top.symbol:
        txt = open(os.path.join(d, f"{sym}.md")).read()
        conv = re.search(r"Conviction:\**\s*(\d+)\s*/\s*100", txt)
        adv = re.search(r"Advance:\**\s*(yes|no)", txt, re.I)
        if not (conv and adv):
            raise ValueError(f"{sym}: note lacks a Conviction or Advance line")
        row = dict(symbol=sym, conviction=int(conv.group(1)), advance=adv.group(1).lower() == "yes")
        if meta is not None and sym in meta.index:
            row.update(verdict=meta.loc[sym, "verdict"], key_window_risk=meta.loc[sym, "key_window_risk"])
        rows.append(row)
    df = pd.DataFrame(rows).sort_values(["advance", "conviction"], ascending=[False, False])
    df.to_csv(os.path.join(d, "ranked_candidates.csv"), index=False)
    with pd.option_context("display.width", 250, "display.max_colwidth", 70):
        print(df.to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
