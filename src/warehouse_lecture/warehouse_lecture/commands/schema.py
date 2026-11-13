"""RobotCommand schema (pydantic) shared by the parser, the executor and the dialog manager.

The pydantic model is what Structured Outputs enforces; ``validate()`` then checks the
*meaning* against the world (known places, objects, poses) and fills defaults, which a
JSON schema cannot do. ``to_msg``/``from_msg`` convert to warehouse_interfaces/RobotCommand.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from warehouse_interfaces.msg import KeyValue, RobotCommand as RobotCommandMsg

# PinkLAB booth (RoboWorld 2026): three cups and the places in src/warehouse_lecture/worlds/locations.yaml.
# The name PARCELS is kept from the lecture code: here it is the list of things the robot can carry (cups).
PARCELS = ("cup_pink", "cup_blue", "cup_yellow")
FIND_TARGETS = ("person",) + PARCELS
ARM_POSES = ("ready", "hands_up", "transport", "home")
GRIPPER = ("open", "close")
STATIONS = ("drinks", "consult_1", "consult_2")          # where the robot can dock, pick and place
PLACE_KO = {"home": "대기 위치", "drinks": "음료대", "consult_1": "1번 상담 테이블", "consult_2": "2번 상담 테이블", "info": "인포데스크",
            "table_a": "테이블 A", "table_b": "테이블 B", "pharmacy": "약국", "classroom_1": "교실1", "classroom_2": "교실2",
            "entrance": "주출입구", "pole": "원기둥 배너"}
TARGET_KO = {"cup_pink": "분홍 컵", "cup_blue": "파란 컵", "cup_yellow": "노란 컵", "person": "사람"}


class Intent(str, Enum):
    move_object = "move_object"
    go_to = "go_to"
    find = "find"
    report = "report"
    answer = "answer"
    arm_pose = "arm_pose"
    gripper = "gripper"
    stop = "stop"


class Place(str, Enum):
    none = ""
    home = "home"
    drinks = "drinks"
    consult_1 = "consult_1"
    consult_2 = "consult_2"
    info = "info"
    table_a = "table_a"
    table_b = "table_b"
    pharmacy = "pharmacy"
    classroom_1 = "classroom_1"
    classroom_2 = "classroom_2"
    entrance = "entrance"
    pole = "pole"


class Attributes(BaseModel):
    helmet: Optional[str] = Field(None, description='"true" 또는 "false"')
    vest: Optional[str] = Field(None, description="orange | green | none")


class RobotCommand(BaseModel):
    """One structured command. Field names match warehouse_interfaces/RobotCommand."""

    intent: Intent
    target: str = Field("", description="물체(cup_pink 등)·person·자세(ready, hands_up, transport, home)·그리퍼(open, close)")
    source: Place = Place.none
    destination: Place = Place.none
    attributes: Attributes = Field(default_factory=Attributes)
    reply: str = Field("", description="사용자에게 할 한 문장 (되묻기·거부 포함)")

    # --- semantic validation ------------------------------------------------
    def validate_world(self):
        """Fill defaults and return a list of problems (empty = executable)."""
        problems = []
        i = self.intent
        if i == Intent.move_object:
            if self.target not in PARCELS:
                problems.append(f"옮길 컵이 정해지지 않았다: {self.target!r} (cup_pink/blue/yellow)")
            if self.source == Place.none:
                self.source = Place.drinks
            if self.destination == Place.none:
                problems.append("어디로 옮길지 정해지지 않았다")
            elif self.source.value not in STATIONS or self.destination.value not in STATIONS:
                problems.append("컵은 음료대 · 1번 상담 테이블 · 2번 상담 테이블 사이에서만 옮길 수 있다")
            if self.source == self.destination:
                problems.append("출발 작업대와 도착 작업대가 같다")
        elif i == Intent.go_to:
            if self.destination == Place.none:
                problems.append("목적지가 없다")
        elif i == Intent.find:
            if self.target not in FIND_TARGETS:
                problems.append(f"찾을 대상이 정해지지 않았다: {self.target!r}")
        elif i == Intent.arm_pose:
            if self.target not in ARM_POSES:
                problems.append(f"모르는 팔 자세 {self.target!r} ({', '.join(ARM_POSES)})")
        elif i == Intent.gripper:
            if self.target not in GRIPPER:
                problems.append(f"그리퍼는 open/close 만 된다: {self.target!r}")
        return problems

    def attribute_dict(self):
        return {k: v for k, v in self.attributes.model_dump().items() if v}

    # --- ROS conversion -----------------------------------------------------
    def to_msg(self, utterance="", request_id=""):
        msg = RobotCommandMsg()
        msg.request_id, msg.intent, msg.target = request_id, self.intent.value, self.target
        msg.source, msg.destination, msg.utterance = self.source.value, self.destination.value, utterance
        msg.params = [KeyValue(key=k, value=str(v)) for k, v in self.attribute_dict().items()]
        if self.reply:
            msg.params.append(KeyValue(key="reply", value=self.reply))
        return msg

    @classmethod
    def from_msg(cls, msg):
        params = {kv.key: kv.value for kv in msg.params}
        return cls(intent=Intent(msg.intent), target=msg.target, source=Place(msg.source or ""), destination=Place(msg.destination or ""),
                   attributes=Attributes(helmet=params.get("helmet"), vest=params.get("vest")), reply=params.get("reply", ""))

    def describe(self):
        """Short Korean description for logs and confirmations."""
        t = TARGET_KO.get(self.target, self.target)
        if self.intent == Intent.move_object:
            return f"{t}를 {self.source.value}에서 {self.destination.value}로 옮기기"
        if self.intent == Intent.go_to:
            return f"{self.destination.value}로 이동"
        if self.intent == Intent.find:
            return f"{t} 찾기 {self.attribute_dict() or ''}".strip()
        return f"{self.intent.value} {self.target}".strip()
