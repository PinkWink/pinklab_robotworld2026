#!/usr/bin/env python3
"""Lesson 10-1: the same sentence, planned with and without the cup table (no simulator).

    ./scripts/robotworld exec python lessons/10_final_project/01_world_plan.py
    ./scripts/robotworld exec python lessons/10_final_project/01_world_plan.py --only world

Each case gives a belief (where each cup is) and a sentence. The planner runs twice:
  - "none":  PlanParser.parse(text)               -> the planner has to guess where the cups are
  - "world": PlanParser.parse(text, world=world)  -> the table is in the system prompt
A case passes when the pick/place locations match and WorldState.check(plan) finds nothing. For a cup
that is already at the destination nothing may run: empty steps, or check() says "이미 ... 에 있다". Writes artifacts/lessons/10_world_plan.json.
"""
import argparse
import json
import time
from pathlib import Path

from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.commands.world import WorldState

D, C1, C2 = "drinks", "consult_1", "consult_2"
START = {"cup_pink": D, "cup_blue": D, "cup_yellow": D}
PINK_MOVED = {"cup_pink": C2, "cup_blue": D, "cup_yellow": D}
TWO_MOVED = {"cup_pink": C2, "cup_blue": C1, "cup_yellow": D}
CASES = [  # (belief, sentence, expected [(action, target, location)] for pick/place only; [] = no steps)
    (START, "분홍 컵 2번 테이블로 가져다 드려", [("pick", "cup_pink", D), ("place", "", C2)]),
    (PINK_MOVED, "파란 컵은 1번 테이블로", [("pick", "cup_blue", D), ("place", "", C1)]),
    (PINK_MOVED, "분홍 컵 다시 음료대로 가져와", [("pick", "cup_pink", C2), ("place", "", D)]),
    (PINK_MOVED, "분홍 컵을 1번 테이블로 옮겨", [("pick", "cup_pink", C2), ("place", "", C1)]),
    (PINK_MOVED, "분홍 컵 2번 테이블로 가져다 드려", []),
    (TWO_MOVED, "파란 컵 원래 자리로 돌려놔", [("pick", "cup_blue", C1), ("place", "", D)]),
    (TWO_MOVED, "흰 옷 입은 손님께 음료 한 잔 가져다 드려", [("pick", "cup_yellow", D), ("place", "", C2)]),
    (TWO_MOVED, "분홍 컵이랑 파란 컵 음료대로 치워 줘",
     [("pick", "cup_pink", C2), ("place", "", D), ("pick", "cup_blue", C1), ("place", "", D)]),
]


def picks_places(plan):
    return [(s.action.value, s.target if s.action.value == "pick" else "", s.location.value)
            for s in plan.steps if s.action.value in ("pick", "place")]


def fmt(pp):
    return " > ".join(f"{a}:{t}@{l}" if t else f"{a}@{l}" for a, t, l in pp) or "(steps 없음)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["none", "world"], help="한쪽만 실행")
    a = ap.parse_args()
    parser = PlanParser()
    modes = [a.only] if a.only else ["none", "world"]
    rows = []
    for mode in modes:
        print(f"\n== {mode}: {'컵 위치표 없이' if mode == 'none' else '컵 위치표를 프롬프트에'}")
        for i, (belief, text, want) in enumerate(CASES, 1):
            world = WorldState(belief)
            t0 = time.monotonic()
            plan = parser.parse(text, world=world if mode == "world" else None)
            dt = time.monotonic() - t0
            problems = plan.validate_world() + (world.check(plan) if plan.steps else [])
            got = picks_places(plan)
            if want:
                ok = got == want and not problems
            else:                       # "already there": nothing may run (empty steps, or the code check refuses)
                ok = not got or any("이미" in p for p in problems)
            rows.append({"mode": mode, "world": world.describe(), "text": text, "ok": ok, "want": fmt(want),
                         "got": fmt(got), "problems": problems, "reply": plan.reply, "seconds": round(dt, 2)})
            print(f"{i} {'ok' if ok else 'XX'} {dt:4.1f}s  [{world.describe()}]  {text}", flush=True)
            if not ok:
                print(f"      want: {fmt(want)}\n      got : {fmt(got)}  {problems or ''}")
            elif not want:
                print(f"      {'; '.join(problems) or plan.reply}")
    for mode in modes:
        n = sum(r["ok"] for r in rows if r["mode"] == mode)
        print(f"{mode:5s}: {n}/{len(CASES)}")
    print(f"cost ${parser.llm.session_cost:.4f}")
    out = Path("artifacts/lessons")
    out.mkdir(parents=True, exist_ok=True)
    (out / "10_world_plan.json").write_text(json.dumps({"cost": parser.llm.session_cost, "rows": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
