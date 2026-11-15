#!/usr/bin/env python3
"""Lesson 08-5 (LLM -> ROS 2 Task Pipeline): one instruction -> RobotPlan (ordered steps), without the simulator.

    ./scripts/robotworld exec python lessons/08_lmm/05_plan.py
    ./scripts/robotworld exec python lessons/08_lmm/05_plan.py "파란 컵은 1번 테이블, 노란 컵은 2번 테이블로"

RobotCommand (lesson 08-2) is one action per sentence. RobotPlan is a list of steps the Task Manager runs in order:
navigate / pick / place / arm_pose / gripper / report / answer (detect exists in the schema; the booth planner does not use it). The LLM still never outputs joints or speeds.
RobotPlan.validate_world() checks the order against the world: it inserts a missing navigate before pick/place, fills
the station, and rejects a place with nothing held, a second pick while holding, or a plan that ends holding a cup.
"""
import sys
import time

from warehouse_lecture.commands.plan import PlanStep, RobotPlan
from warehouse_lecture.commands.plan_parser import PlanParser

DEFAULT = ["입구 쪽 테이블 손님께 파란 컵 가져다 드려",        # 별명 (입구 쪽 테이블 = consult_2): 네 단계로 펼쳐진다
           "노란 컵 1번 테이블로",                           # 짧은 지령
           "약국으로 가서 주변 상황 알려줘",                 # 이동 + 보고 (pick/place 없음 → 확인 없이 실행)
           "옮겨 줘"]                                        # 무엇을? → steps 비움, 되묻기
# (plan_parser.py 의 예시 3 개와 겹치지 않는 문장들)


def show(plan, problems):
    for i, st in enumerate(plan.steps, 1):
        key = " ".join(x for x in (st.action.value, st.target, f"@{st.location.value}" if st.location.value else "") if x)
        print(f"   {i}. {key:34s} {st.note or st.describe()}")
    if problems:
        print(f"   validate_world: {'; '.join(problems)}")
    elif plan.steps:
        print(f"   validate_world: ok   (confirm first: {plan.needs_confirmation()})")
    if plan.reply:
        print(f"   reply: {plan.reply}")


def main():
    print("1) validate_world() without the LLM")
    hand = RobotPlan(steps=[PlanStep(action="pick", target="cup_pink"), PlanStep(action="place", location="consult_2")])
    print(">> [pick cup_pink, place @consult_2]   (no navigate written)")
    show(hand, hand.validate_world())
    bad = RobotPlan(steps=[PlanStep(action="navigate", location="consult_1"), PlanStep(action="place", location="consult_1")])
    print(">> [navigate consult_1, place @consult_1]   (nothing picked)")
    show(bad, bad.validate_world())
    parser = PlanParser()
    print("\n2) LLM -> RobotPlan -> validate_world()")
    for text in sys.argv[1:] or DEFAULT:
        t0 = time.monotonic()
        plan = parser.parse(text)
        print(f"\n>> {text}   ({time.monotonic() - t0:.2f} s, {len(plan.steps)} steps)")
        show(plan, plan.validate_world())
    print(f"\ncost this run ${parser.llm.session_cost:.5f}")


if __name__ == "__main__":
    main()
