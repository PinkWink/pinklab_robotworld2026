"""Korean utterance -> RobotCommand with OpenAI Structured Outputs (promoted from M3 example 06)."""

from ..llm.client import LLM
from .schema import RobotCommand

SYSTEM = """너는 로보월드 2026 핑크랩 부스의 안내 · 서빙 로봇의 명령 해석기다. 사용자의 한국어 문장을 RobotCommand 로 바꾼다.
의도(intent): move_object(컵을 옮김) | go_to(장소로 이동) | find(사람·컵 찾기) | report(주변 상황 보고) | answer(질문 답변, 되묻기, 거부) | arm_pose(팔 자세) | gripper(그리퍼) | stop(정지)
장소: home(대기 위치, 홈, 처음 자리), drinks(음료대, 음료 스테이션), consult_1(상담 테이블 1, 1번 테이블, 안쪽 상담 테이블), consult_2(상담 테이블 2, 2번 테이블, 입구 쪽 상담 테이블), info(인포, 안내 데스크), table_a(테이블 A, 펜듈럼 테이블), table_b(테이블 B, 픽앤플레이스 테이블), pharmacy(약국, 태전약품), classroom_1(교실1, 핑키 스튜디오), classroom_2(교실2, 피지컬 AI 스튜디오), entrance(입구, 주출입구), pole(원기둥, 배너 기둥)
물체(target): cup_pink(분홍 컵), cup_blue(파란 컵), cup_yellow(노란 컵), person. 팔 자세(target): ready(준비), hands_up(들어 올림), transport(운반/주행), home. 그리퍼(target): open, close
컵은 drinks · consult_1 · consult_2 사이에서만 옮긴다. 출발지가 문장에 없으면 source 는 비워 둔다(기본값 drinks 가 채워진다).
규칙: 특정 대상(사람·컵)이 있는지, 어디 있는지 묻거나 위치를 확인하라는 말은 find 다. '상황/상태/주변/브리핑' 을 보고·알려 달라는 말은 report 다. 컵 색(분홍/파랑/노랑)이나 목적지가 문장에 없으면 절대 추측하지 말고 intent=answer 로 되묻는다. 되묻는 중이면 앞 문장과 답을 합쳐 해석한다('컵 옮겨 / 파란 거 2번 테이블' = 파란 컵을 2번 테이블로). 사람이나 물건을 해치거나 위험한 요청은 intent=answer 로 거부한다. 과거 기억을 묻는 질문(아까, 전에, 어디 있었지)과 로봇 자신 · 부스에 대한 질문은 intent=answer.
reply 에는 사용자에게 할 한 문장을 쓴다(실행 명령이면 무엇을 할지, answer 면 답·되묻기·거부)."""

EXAMPLES = [
    ("분홍 컵 2번 테이블로 가져다 드려", RobotCommand(intent="move_object", target="cup_pink", destination="consult_2", reply="분홍 컵을 2번 상담 테이블로 가져다 드리겠습니다.")),
    ("팔 운반 자세로", RobotCommand(intent="arm_pose", target="transport", reply="팔을 운반 자세로 바꿉니다.")),
    ("노란 컵 어디 있어?", RobotCommand(intent="find", target="cup_yellow", reply="노란 컵을 찾겠습니다.")),
    ("컵 옮겨", RobotCommand(intent="answer", reply="어떤 색 컵을 어느 테이블로 옮길까요?")),
]


class CommandParser:
    def __init__(self, llm=None, history=None):
        self.llm = llm or LLM()

    def parse(self, text, context=None):
        """context: optional list of prior (user, assistant) turns for slot filling (dialog manager)."""
        messages = [{"role": "system", "content": SYSTEM}]
        for q, cmd in EXAMPLES:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": cmd.model_dump_json()})
        for user, assistant in (context or []):
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": text})
        return self.llm.parse(messages, RobotCommand, temperature=0.0, purpose="command_parse")
