"""Input tokens of one command-parse request, measured by adding its parts one by one (4 API calls).

    ./scripts/robotworld exec python docs/camp/measure_lesson12_tokens.py > artifacts/docs/l12_tokens.log
"""
import json

from warehouse_lecture.commands.parser import EXAMPLES, SYSTEM
from warehouse_lecture.commands.schema import RobotCommand
from warehouse_lecture.llm.client import LLM

TEXT = "분홍 컵 2번 테이블로 가져다 드려"
llm = LLM()
model = llm.models["chat"]
user = [{"role": "user", "content": TEXT}]
system = [{"role": "system", "content": SYSTEM}]
shots = []
for q, cmd in EXAMPLES:
    shots += [{"role": "user", "content": q}, {"role": "assistant", "content": cmd.model_dump_json()}]


def count(messages, schema=None):
    if schema:
        r = llm.client.chat.completions.parse(model=model, messages=messages, response_format=schema, temperature=0.0, max_tokens=200)
    else:
        r = llm.client.chat.completions.create(model=model, messages=messages, temperature=0.0, max_tokens=1)
    return [r.usage.prompt_tokens, r.usage.completion_tokens]


print(json.dumps({"user_only": count(user), "system_user": count(system + user), "system_fewshot_user": count(system + shots + user),
                  "full_parse": count(system + shots + user, RobotCommand)}))
