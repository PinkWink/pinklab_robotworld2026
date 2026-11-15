#!/usr/bin/env python3
"""Lesson 08-1 (LMM + OpenAI API): one chat call, its tokens, cost and latency.

    ./scripts/robotworld exec python lessons/08_lmm/01_hello.py
    ./scripts/robotworld exec python lessons/08_lmm/01_hello.py "컵을 옮길 때 무엇을 조심해야 해?"

Needs OPENAI_API_KEY in the workspace .env (copy .env.example). Model names and prices: src/warehouse_lecture/config/llm.yaml.
Every call goes through warehouse_lecture.llm.client.LLM, which appends one line per call to logs/openai_usage.jsonl.
"""
import json
import sys
import time

from warehouse_lecture.llm.client import LLM

SYSTEM = ("너는 로보월드 2026 핑크랩 부스의 안내 · 서빙 로봇의 두뇌다. 로봇에는 카메라 2대, 라이다, 양팔이 있고 컵을 집어 테이블로 옮길 수 있다. "
          "답은 한국어로, 두 문장 이내로 간결하게 한다.")


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "손님이 길을 막고 서 있으면 어떻게 해야 해?"
    llm = LLM()
    print(f"model: {llm.models['chat']}   log: {llm.log_path}")
    t0 = time.monotonic()
    answer = llm.chat([{"role": "system", "content": SYSTEM},            # 역할 · 규칙 (매 요청에 함께 간다)
                       {"role": "user", "content": question}],
                      temperature=0.2, max_tokens=120, purpose="lesson08_hello")
    seconds = time.monotonic() - t0
    print(f"user : {question}")
    print(f"robot: {answer}")
    last = json.loads(llm.log_path.read_text().splitlines()[-1])        # the line this call just wrote
    print(f"tokens: input {last['input_tokens']} + output {last['output_tokens']}   cost ${last['cost_usd']:.6f}   {seconds:.2f} s")
    print(f"log line: {json.dumps(last, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
