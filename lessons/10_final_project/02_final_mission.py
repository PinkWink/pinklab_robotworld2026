#!/usr/bin/env python3
"""Lesson 10-2 (Final Mission): sentence -> LLM plan (with the cup table) -> confirm -> Task Manager
-> Nav2 / PickPlace(MoveIt) -> MuJoCo -> result sentence, and the table is updated for the next sentence.

    (terminal 1: ./scripts/robotworld start - it also runs the Task Manager)
    ./scripts/robotworld exec python lessons/10_final_project/02_final_mission.py               # the three scenarios
    ./scripts/robotworld exec python lessons/10_final_project/02_final_mission.py --scenario 3  # one of them
    ./scripts/robotworld exec python lessons/10_final_project/02_final_mission.py --keyboard    # type, empty line ends
    ./scripts/robotworld exec python lessons/10_final_project/02_final_mission.py --dry-run     # no simulator: assume success

Scenarios (the cups start on the drinks stand):
  1. 분홍 컵: 음료대 -> 2번 상담 테이블
  2. 음료 한 잔: 되묻기 한 번 (어느 테이블?) -> 안쪽 테이블 = 1번. 컵은 음료대에 남은 것 중에서 플래너가 고른다
  3. 분홍 컵을 다시 음료대로 -- the planner must read the table (pink is on consult table 2 now)
Writes artifacts/lessons/10_final_mission.json (turns, steps, seconds, world before/after, LLM cost).
"""
import argparse
import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace

from warehouse_lecture.commands.dialog import PlanDialogManager
from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.commands.world import WorldState
from warehouse_lecture.llm.client import LLM

SCENARIOS = {
    1: ["음료대로 가서 분홍 컵을 집고 2번 상담 테이블에 가져다 드려", "응"],
    2: ["손님께 음료 한 잔 가져다 드려", "안쪽 테이블", "응"],
    3: ["분홍 컵 다시 음료대로 가져와", "응"],
}


def plan_client():
    """PlanClient from lessons/08_lmm/07_run_plan.py (ExecutePlan action client with feedback print)."""
    path = Path(__file__).resolve().parents[1] / "08_lmm" / "07_run_plan.py"
    spec = importlib.util.spec_from_file_location("run_plan", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", type=int, choices=sorted(SCENARIOS), action="append", help="골라서 실행 (여러 번 가능)")
    ap.add_argument("--keyboard", action="store_true", help="문장을 직접 입력")
    ap.add_argument("--dry-run", action="store_true", help="시뮬레이터 없이: 모든 단계가 성공했다고 보고 위치표만 갱신")
    a = ap.parse_args()

    node = None
    if not a.dry_run:
        import rclpy
        rclpy.init()
        node = plan_client().PlanClient()

    def speak(text):
        print(f"[robot] {text}", flush=True)

    def execute(plan, text):
        if node is None:
            print("   (dry-run) " + plan.describe().replace("\n", " / "))
            return SimpleNamespace(success=True, steps_done=len(plan.steps), spoken="(dry-run) 모든 단계를 마쳤다고 가정합니다.")
        return node.run(plan, utterance=text)

    llm = LLM()
    world = WorldState()
    dm = PlanDialogManager(PlanParser(llm), executor=execute, speak=speak, world=world)
    log = []

    def turn(text):
        before = world.describe()
        t0 = time.monotonic()
        action, reply, plan = dm.handle(text)
        log.append({"text": text, "action": action, "seconds": round(time.monotonic() - t0, 1),
                    "steps": [s.note or s.describe() for s in plan.steps], "reply": reply,
                    "world_before": before, "world_after": world.describe()})
        print(f"    ({action}; {time.monotonic() - t0:.1f}s)")

    print(f"[world] {world.describe()}")
    if a.keyboard:
        while True:
            try:
                text = input("[user] ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                break
            turn(text)
            print(f"[world] {world.describe()}")
    else:
        for n in a.scenario or sorted(SCENARIOS):
            print(f"\n===== 시나리오 {n}")
            dm.context.clear()          # each scenario is a new conversation; the world table carries over
            for text in SCENARIOS[n]:
                print(f"[user] {text}")
                turn(text)
            print(f"[world] {world.describe()}")

    runs = [t for t in log if t["action"] == "result"]
    print(f"\n턴 {len(log)}개, 실행 {len(runs)}회, 실행 시간 {sum(t['seconds'] for t in runs):.0f}s, LLM 비용 ${llm.session_cost:.4f}")
    out = Path("artifacts/lessons")
    out.mkdir(parents=True, exist_ok=True)
    (out / "10_final_mission.json").write_text(json.dumps({"cost": llm.session_cost, "turns": log}, ensure_ascii=False, indent=1))
    if node is not None:
        import rclpy
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
