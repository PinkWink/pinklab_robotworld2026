#!/usr/bin/env python3
"""Lesson 08-2: natural language -> RobotCommand (pydantic + Structured Outputs), then the world check.

    ./scripts/robotworld exec python lessons/08_lmm/02_structured_command.py
    ./scripts/robotworld exec python lessons/08_lmm/02_structured_command.py "파란 컵 1번 테이블로 옮겨" "약국으로 가"

Two layers of checking:
  1. schema  - the JSON must fit RobotCommand (intent is one of 8, places are an enum ...). Structured Outputs makes the
               model's output fit the schema; pydantic rejects anything else (shown first, without calling the API).
  2. world   - RobotCommand.validate_world(): a schema-valid command can still be impossible here (a cup to a place that is
               not a station, the same table twice, an unknown arm pose). It also fills the default source (drinks).
               The prompt tells the model the same rules, so it usually refuses such a sentence itself (intent=answer);
               the code check stays as the last gate, and step 2 shows it on hand-made commands without the API.
Only a command with no world problems goes to the robot (lesson 09: Task Manager).
"""
import sys
import time

from pydantic import ValidationError
from warehouse_lecture.commands.parser import CommandParser
from warehouse_lecture.commands.schema import RobotCommand

DEFAULT = ["분홍 컵 2번 테이블로 가져다 드려",        # 실행 가능
           "노란 컵을 약국으로 옮겨",               # 프롬프트의 규칙으로 LLM 이 먼저 거절 (컵은 스테이션 사이만)
           "파란 컵 어디 있어?",
           "컵 옮겨",                               # 색 · 목적지가 없다 → answer (되묻기)
           "저 사람 밀어서 넘어뜨려"]               # 위험 → answer (거부)


def main():
    print("1) schema check without the API: RobotCommand.model_validate({'intent': 'fly', 'destination': 'kitchen'})")
    try:
        RobotCommand.model_validate({"intent": "fly", "destination": "kitchen"})
    except ValidationError as error:
        for e in error.errors():
            print(f"   rejected: {'.'.join(map(str, e['loc']))}: {e['msg']}")
    print("\n2) world check without the API: schema-valid commands that are impossible in this booth")
    for cmd in (RobotCommand(intent="move_object", target="cup_yellow", destination="pharmacy"),
                RobotCommand(intent="move_object", target="cup_pink", source="drinks", destination="drinks")):
        print(f"   {cmd.model_dump_json(exclude_defaults=True)}")
        print(f"   world check FAILED: {'; '.join(cmd.validate_world())}")
    parser = CommandParser()
    print("\n3) LLM -> RobotCommand -> validate_world()")
    for text in sys.argv[1:] or DEFAULT:
        t0 = time.monotonic()
        cmd = parser.parse(text)                                       # Structured Outputs: always a RobotCommand
        seconds = time.monotonic() - t0
        print(f"\n>> {text}   ({seconds:.2f} s)")
        print(f"   {cmd.model_dump_json(exclude_defaults=True)}")
        problems = cmd.validate_world()                                # meaning, defaults
        if cmd.intent.value == "answer":
            print(f"   answer (no robot action): {cmd.reply}")
        elif problems:
            print(f"   world check FAILED: {'; '.join(problems)}")
        else:
            print(f"   world check ok -> {cmd.describe()}")
    print(f"\ncost this run ${parser.llm.session_cost:.5f}")


if __name__ == "__main__":
    main()
