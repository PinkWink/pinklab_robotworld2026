"""WorldState: what the robot believes about the cups and who sits where (PinkLAB booth).

The LLM planner cannot see the booth. WorldState keeps one line per cup (and the guests at the
consult tables), is written into the planner's system prompt, checks a plan before it runs, and is
updated from the Task Manager result (only the steps that actually finished change the belief).

    world = WorldState()                      # all three cups on the drinks stand
    world.prompt()                            # text for the LLM system prompt
    world.check(plan)                         # [] or ["분홍 컵은 1번 상담 테이블에 있다 (계획: 음료대에서 집기)"]
    world.apply(plan, result.steps_done, result.success)
"""

from .plan import StepAction
from .schema import PARCELS, PLACE_KO, TARGET_KO

HELD = "held"          # in the gripper


def topic(word):
    """Word + topic particle: 은 after a final consonant (컵은), 는 after a vowel (상자는)."""
    code = ord(word[-1]) - 0xAC00 if word else -1
    return word + ("은" if 0 <= code < 11172 and code % 28 else "는")
UNKNOWN = "unknown"    # a pick/place failed half-way: look before trusting the belief


# Who sits at the consult tables (booth design + robotworld scenario.yaml).
GUESTS = {
    "consult_1": "분홍 맨투맨을 입은 남성 (안쪽 테이블)",
    "consult_2": "흰 상의를 입은 여성 손님 (입구 쪽 테이블)",
}


class WorldState:
    def __init__(self, parcels=None, guests=None):
        self.parcels = dict(parcels or {p: "drinks" for p in PARCELS})
        self.guests = dict(GUESTS if guests is None else guests)
        self.history = []     # (before, after) per executed plan

    # --- the planner's view --------------------------------------------------
    def where(self, parcel):
        return self.parcels.get(parcel, UNKNOWN)

    def describe(self):
        """One Korean line, e.g. '분홍 컵: 1번 상담 테이블 · 파란 컵: 음료대 · 노란 컵: 음료대'"""
        return " · ".join(f"{TARGET_KO[p]}: {self._ko(loc)}" for p, loc in self.parcels.items())

    def prompt(self):
        lines = [f"- {p}({TARGET_KO[p]}): {loc}({self._ko(loc)})" for p, loc in self.parcels.items()]
        guests = [f"- {t}({self._ko(t)}): {who}" for t, who in self.guests.items()]
        return ("현재 컵 위치 (로봇이 마지막으로 확인한 것):\n" + "\n".join(lines) + "\n"
                "상담 테이블에 앉은 사람:\n" + "\n".join(guests) + "\n"
                "컵 위치 규칙:\n"
                "- pick 은 그 컵이 지금 있는 곳(이 표)에서 한다. navigate 도 그곳으로 간다.\n"
                "- 손님께 가져다 드릴 때는 음료대(drinks)에 있는 컵을 쓴다. 색을 말하지 않았으면 음료대에 있는 컵 중 첫 번째를 고른다.\n"
                "- 음료대에 컵이 없으면 steps 를 비우고 reply 로 '음료대에 컵이 없다'고 알린다.\n"
                "- 위치가 unknown 인 컵은 쓰지 않는다.\n")

    # --- before running -----------------------------------------------------
    def check(self, plan):
        """Problems between the plan and the belief (empty = consistent). The facts are checked here,
        in code, not by the LLM: wrong source, and a cup that is already at the destination."""
        problems, belief = [], dict(self.parcels)
        held = next((p for p, loc in belief.items() if loc == HELD), None)
        origin = {}
        for step in plan.steps:
            if step.action == StepAction.pick:
                loc = belief.get(step.target, UNKNOWN)
                origin[step.target] = loc
                if loc not in (step.location.value, UNKNOWN, HELD):
                    origin[step.target] = "wrong_source"
                    problems.append(f"{topic(TARGET_KO.get(step.target, step.target))} {self._ko(loc)}에 있다 "
                                    f"(계획: {self._ko(step.location.value)}에서 집기)")
                belief[step.target], held = HELD, step.target
            elif step.action == StepAction.place and held:
                if belief.get(held) == HELD and self.parcels.get(held) == step.location.value:
                    if origin.get(held) == "wrong_source":
                        problems.pop()      # say the simpler thing instead
                    problems.append(f"{topic(TARGET_KO.get(held, held))} 이미 {self._ko(step.location.value)}에 있다")
                belief[held], held = step.location.value, None
        return problems

    # --- after running ------------------------------------------------------
    def apply(self, plan, steps_done, success):
        """Replay the finished steps. A failed pick/place leaves that cup UNKNOWN."""
        before = dict(self.parcels)
        held = next((p for p, loc in self.parcels.items() if loc == HELD), None)
        for i, step in enumerate(plan.steps):
            if i < steps_done:
                if step.action == StepAction.pick and step.target in self.parcels:
                    self.parcels[step.target], held = HELD, step.target
                elif step.action == StepAction.place and held:
                    self.parcels[held], held = step.location.value, None
            elif i == steps_done and not success:
                if step.action == StepAction.pick and step.target in self.parcels:
                    self.parcels[step.target] = UNKNOWN
                elif step.action == StepAction.place and held:
                    self.parcels[held] = UNKNOWN
                break
        self.history.append((before, dict(self.parcels)))
        return self.parcels

    @staticmethod
    def _ko(loc):
        return {HELD: "그리퍼(들고 있음)", UNKNOWN: "확인 필요"}.get(loc, PLACE_KO.get(loc, loc))
