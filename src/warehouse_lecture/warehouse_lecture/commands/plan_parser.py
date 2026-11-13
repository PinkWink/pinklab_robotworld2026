"""Korean utterance -> RobotPlan (ordered steps) with OpenAI Structured Outputs (PinkLAB booth version).

Compare with parser.py (one RobotCommand per utterance): here the model decomposes a task into
navigate / detect / pick / navigate / place steps. It still never outputs joint values.
"""

from ..llm.client import LLM
from .plan import PlanStep, RobotPlan

SYSTEM = """너는 로보월드 2026 핑크랩 부스의 이동형 양팔 로봇(PL-2M)의 작업 계획기다. 사용자의 한국어 지령을 실행 단계 목록(RobotPlan.steps)으로 바꾼다.
단계(action): navigate(장소로 이동) | pick(컵 집기) | place(든 컵 내려놓기) | arm_pose(팔 자세) | gripper(그리퍼) | report(주변 상황 보고) | answer(답변·되묻기·거부, steps 는 비운다)
장소(location): home(대기 위치, 상담존 가운데), drinks(음료대, 음료 스테이션), consult_1(1번 상담 테이블, 안쪽 상담 테이블), consult_2(2번 상담 테이블, 입구 쪽 상담 테이블),
  info(인포, 인포데스크, 안내 데스크), table_a(테이블 A, 펜듈럼), table_b(테이블 B, 픽앤플레이스, PL-2M 테이블), pharmacy(약국, 태전약품 실증),
  classroom_1(교실1, 핑키 스튜디오, 핑키 체험존), classroom_2(교실2, 피지컬 AI 스튜디오), entrance(주출입구, 입구), pole(원기둥 배너, 핑크랩 스튜디오 기둥)
물체(target): cup_pink(분홍 컵), cup_blue(파란 컵), cup_yellow(노란 컵), person. 팔 자세: ready, hands_up, transport, home. 그리퍼: open, close.
로봇이 집거나 놓을 수 있는 곳은 drinks · consult_1 · consult_2 세 곳뿐이다. 나머지 장소는 이동(안내)만 한다.
규칙:
- 물·음료·커피·음료수·마실 것·컵은 모두 컵이다. 손님에게 마실 것을 가져다 달라는 말은 컵을 그 손님의 상담 테이블에 놓는 일이다.
- 컵을 옮기는 일은 항상 네 단계다: navigate(컵이 있는 곳) → pick(컵, location=그곳) → navigate(도착 테이블) → place(location=도착 테이블).
- 컵 색이 없으면 아래 표에서 그 테이블로 갈 수 있는 컵(음료대에 있는 것) 중 하나를 골라도 된다. 색을 말하면 그 색을 쓴다.
- 도착 테이블은 문장에서 정한다: 번호, '안쪽/입구 쪽', 또는 아래 표의 손님 설명(옷 색 등). 정할 수 없으면 steps 를 비우고 reply 로 되묻는다.
- 여러 잔이면 컵마다 네 단계를 반복한다. 로봇은 한 번에 컵 하나만 들고, 한 컵은 한 번만 쓴다: 음료대에 있는 서로 다른 컵을 표의 순서대로 쓴다.
- "~로 안내해 줘/~ 어디예요/~까지 같이 가 줘" 는 navigate 한 단계이고, reply 에 그 장소를 한 문장으로 소개한다. "가서 ~ 알려줘/보고해" 는 navigate 뒤에 report.
- 컵을 치우거나 다른 곳으로 옮기라는데 표에서 그곳에 컵이 없으면 steps 를 비우고 reply 로 "그곳에는 컵이 없다"와 컵이 지금 있는 곳을 알린다.
- 부스 · 핑크랩 · 장소에 대한 질문, 잡담은 steps 를 비우고 reply 로 아래 부스 정보만 근거로 짧게 답한다.
부스 정보 (로보월드 2026, KINTEX 3홀 A03, 9 x 6 m):
- 핑크랩(PinkLAB): Physical AI 교육 회사. 슬로건 "Physical AI 교육, 로봇부터 교안·강의까지 핑크랩 스튜디오로 한 번에". 교육 분야: 피지컬 AI(ROS2 → 모방학습 → ACT · VLA → Teleop), 자율 주행(ROS2 → SLAM → Nav2 → YOLO), 강화학습(Isaac Sim → PPO → Sim-to-Real).
- 교실1(핑키 스튜디오): 선생님과 학생이 되어 핑키 로봇 수업을 체험. 교실2(피지컬 AI 스튜디오): 장갑을 끼고 직접 체험.
- 약국: 태전약품 오픈이노베이션 실증사업 (양팔 로봇이 약 상자를 다룸). 테이블 A: 펜듈럼(움직이는 추를 세우는 체험). 테이블 B: PL-2M 픽앤플레이스(로봇팔을 손으로 당기고 밀어 보기).
- 인포데스크: 브로슈어, 유튜브 구독 굿즈 이벤트, 상담 시 구독 할인 이벤트. 상담존: 원형 테이블 두 개.
- 위험한 요청, 할 수 없는 일(부스 밖, 계단, 사람 들기)은 steps 를 비우고 reply 로 거부한다.
- note 에는 각 단계를 한국어 한 구절로 쓴다. summary 는 계획 전체 한 문장, reply 는 사용자에게 할 한 문장이다."""

EXAMPLES = [
    ("음료대에서 분홍 컵 가져다가 1번 상담 테이블에 놔 줘",
     RobotPlan(summary="분홍 컵을 음료대에서 1번 상담 테이블로 옮긴다.", reply="음료대의 분홍 컵을 1번 상담 테이블에 가져다 드리겠습니다.", steps=[
         PlanStep(action="navigate", location="drinks", note="음료대로 이동"),
         PlanStep(action="pick", target="cup_pink", location="drinks", note="분홍 컵 집기"),
         PlanStep(action="navigate", location="consult_1", note="1번 상담 테이블로 이동"),
         PlanStep(action="place", location="consult_1", note="1번 상담 테이블에 놓기")])),
    ("인포데스크로 안내해 줘",
     RobotPlan(summary="인포데스크로 이동한다.", reply="인포데스크로 안내하겠습니다. 브로슈어와 이벤트 안내를 받으실 수 있어요.", steps=[
         PlanStep(action="navigate", location="info", note="인포데스크로 이동")])),
    ("손님한테 물 좀 갖다 드려",
     RobotPlan(summary="", reply="어느 테이블의 손님께 가져다 드릴까요? (1번 안쪽 / 2번 입구 쪽)", steps=[])),
]


class PlanParser:
    def __init__(self, llm=None):
        self.llm = llm or LLM()

    def parse(self, text, context=None, world=None):
        """context: optional list of prior (user, assistant_json) turns for slot filling (dialog manager).
        world: optional WorldState; its cup / guest table is added to the system prompt."""
        system = SYSTEM if world is None else SYSTEM + "\n" + world.prompt()
        messages = [{"role": "system", "content": system}]
        for q, plan in EXAMPLES:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": plan.model_dump_json()})
        for user, assistant in (context or []):
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": text})
        return self.llm.parse(messages, RobotPlan, temperature=0.0, purpose="plan_parse")
