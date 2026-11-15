"""Figures for the web FMS page (booth version of lesson 14). Output: docs/camp/lesson14_*.png

    ./scripts/robotworld exec python docs/camp/draw_lesson14_figures.py
Data (2026-11-16, artifacts/docs/l18_fms.sh): page screenshots artifacts/dev/fms_frames/f*.png (headless Chrome, every 2 s),
artifacts/docs/l18_events.log (seconds since the first frame + what the script did), l18_api_*.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = Path("docs/camp")
FRAMES = Path("artifacts/dev/fms_frames")
EVENTS = [(int(l.split(" ", 1)[0]), l.split(" ", 1)[1].strip()) for l in Path("artifacts/docs/l18_events.log").read_text().splitlines()]
BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"


def t_of(name):
    return next(t for t, n in EVENTS if n == name)


def frame(t):
    """Screenshot nearest to t seconds after the first frame (one frame every 2 s)."""
    files = sorted(FRAMES.glob("f*.png"))
    return Image.open(files[max(0, min(len(files) - 1, round(t / 2)))]).convert("RGB")


# ================================================================ 1. 개념
def why():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.35, "웹 FMS: 터미널 여러 개로 하던 일을 브라우저 한 화면에서", bold=True, fs=12)
    tiles(ax, [("보기", ["부스 지도 · 로봇 위치 (AMCL)", "Nav2 경로 · 라이다 점 · 컵 위치", "카메라 영상 (켰을 때만)"], C["blue"]),
               ("움직이기", ["수동 조작: 누르는 동안만 /cmd_vel", "지도 클릭 · 장소 버튼 → Nav2 goal", "정지 버튼: Nav2 · 미션 · 수동 모두 중지"], C["green"]),
               ("시키기", ["문장 → LLM 계획 → 단계 확인 → 실행", "Task Manager 의 단계 진행을 채팅에 표시", "끝나면 컵 위치 표를 고침"], C["yellow"])],
          cols=3, y_top=3.9, gap=0.3, h=2.2, tfs=11, fs=9)
    note(ax, 0.3, 1.25, "앞 글의 PlanDialogManager · PlanParser · Task Manager 를 그대로 쓴다. 새로 만든 것은 fms/server.py 한 파일과 정적 페이지 (HTML · JS · CSS).", fs=9.8)
    save(fig, "lesson14_why.png")


def arch():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.75, "프로세스 하나: Flask (HTTP) + rclpy 노드 (배경 스레드). 브라우저는 ROS 를 모른다.", bold=True, fs=12)
    rbox(ax, 0.3, 1.6, 3.0, 2.6, "브라우저", ["static/index.html", "app.js · style.css", "", "EventSource: 상태 5 Hz", "fetch POST: 명령"], fc=C["grey"], fs=9, dy=0.36)
    rbox(ax, 4.3, 1.6, 4.4, 2.6, "fms/server.py", ["Flask: / · /api/stream (SSE)", "/api/drive · goal · stop · chat · camera", "", "Fms(Node): 콜백이 최신 상태를 dict 에 저장", "잠금 하나 (lock) · snapshot() 으로 읽기"], fc=C["blue"], fs=9, dy=0.36)
    rbox(ax, 9.7, 3.2, 4.0, 1.0, "Nav2", ["/navigate_to_pose · /plan · /amcl_pose"], fc=C["green"], fs=8.8)
    rbox(ax, 9.7, 2.0, 4.0, 1.0, "Task Manager", ["/execute_plan (단계 피드백)"], fc=C["yellow"], fs=8.8)
    rbox(ax, 9.7, 0.8, 4.0, 1.0, "시뮬레이터 (브리지)", ["/cmd_vel · /scan · /odom · 컵 자세 · JPEG 파일"], fc=C["purple"], fs=8.8)
    arrow(ax, (3.3, 3.3), (4.3, 3.3)); arrow(ax, (4.3, 2.5), (3.3, 2.5))
    label(ax, 3.8, 3.55, "POST", fs=8.5); label(ax, 3.8, 2.25, "SSE", fs=8.5)
    for y in (3.7, 2.5, 1.3):
        arrow(ax, (8.7, min(y, 3.9) if y > 1.6 else 1.9), (9.7, y))
    note(ax, 0.3, 0.9, "LLM (OpenAI) 호출은 /api/chat 이 띄운", fs=9.4)
    note(ax, 0.3, 0.5, "작업 스레드 안에서: 페이지는 멈추지 않는다.", fs=9.4)
    save(fig, "lesson14_arch.png")


def flow():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.95, "LLM 지령 한 건의 흐름", bold=True, fs=12)
    chain(ax, [("브라우저", ["문장 입력", "POST /api/chat"]), ("작업 스레드", ["Fms.chat()", "busy = True"]), ("PlanDialogManager", ["LLM 계획 + 컵 위치 표", "되묻기 / 확인 / 실행"]),
               ("확인", ["pending = True", "→ [진행] [취소] 버튼"]), ("execute_plan()", ["/execute_plan goal", "피드백 → mission · chat"]), ("끝", ["결과 문장", "WorldState.apply()"])],
          y=1.3, h=1.9, tfs=10, fs=8.6, gap=0.25, colors=[C["grey"], C["blue"], C["yellow"], C["purple"], C["green"], C["teal"]])
    note(ax, 0.3, 0.75, "모든 변화는 Fms.s (상태 dict) 에 쓰이고, 브라우저는 SSE 로 0.2 s 마다 전체 상태를 받아 다시 그린다. [진행] 버튼은 '응' 을 /api/chat 으로 보낸다.", fs=9.4)
    save(fig, "lesson14_sequence.png")


def owners():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.15, "/cmd_vel 은 하나, 쓰려는 쪽은 셋: 누가 먼저인가", bold=True, fs=12)
    tiles(ax, [("수동 조작", ["버튼 · WASD 를 누르는 동안 0.15 s 마다 POST", "첫 요청에서 Nav2 goal 과 미션을 취소", "0.4 s 동안 요청이 없으면 0 을 한 번 보내고 손을 뗌"], C["green"]),
               ("Nav2 goal", ["지도 클릭 · 장소 버튼", "미션 실행 중이면 409 로 거부", "새 goal 은 앞 goal 을 취소하고 보냄"], C["blue"]),
               ("LLM 미션", ["Task Manager 가 Nav2 · PickPlace 를 부름", "시작할 때 FMS 가 보낸 Nav2 goal 취소", "정지 버튼 → /execute_plan 취소"], C["yellow"])],
          cols=3, y_top=3.7, gap=0.3, h=2.3, tfs=11, fs=9)
    note(ax, 0.3, 0.85, "dead-man: 브라우저 탭이 닫히거나 네트워크가 끊겨도 0.4 s 뒤에 로봇이 선다. 정지 버튼은 세 가지를 모두 멈춘다.", fs=9.6)
    save(fig, "lesson14_owners.png")


def api():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.15, "HTTP API (fms/server.py make_app)", bold=True, fs=12)
    rows = [("GET /api/stream", "SSE: 상태 전체 (pose · twist · plan · scan · cups · nav · mission · chat ...) 0.2 s 마다", C["blue"]),
            ("GET /api/map · map.png", "지도 크기 · 해상도 · 원점, 지도 그림 (PNG)", C["blue"]),
            ("POST /api/drive", "{v, w}: 수동 조작 (누르는 동안 반복)", C["green"]),
            ("POST /api/goal", "{place} 또는 {x, y, yaw}: Nav2 goal", C["green"]),
            ("POST /api/stop", "Nav2 · 미션 · 수동 조작 정지", C["red"]),
            ("POST /api/chat", "{text}: LLM 지령 · 되묻기의 답 · 확인의 '응 / 아니'", C["yellow"]),
            ("POST /api/camera", "{on}: 카메라 JPEG 저장 켜기 / 끄기 → /camera/<이름>.mjpg", C["purple"])]
    for i, (k, v, fc) in enumerate(rows):
        y = 4.4 - i * 0.66
        rbox(ax, 0.3, y, 3.6, 0.54, k, fc=fc, tfs=9.8)
        ax.text(4.15, y + 0.27, v, va="center", fontsize=9.6, color=INK)
    save(fig, "lesson14_api.png")


# ================================================================ 2. 실행 (화면 캡처)
def shot(name, t, crop=None):
    img = frame(t)
    if crop:
        img = img.crop(crop)
    img.save(OUT / name)
    print("saved", name, img.size)


def shots():
    shot("lesson14_layout.png", t_of("page open") + 2)
    shot("lesson14_shot_goal.png", t_of("goal info") + 12)
    shot("lesson14_shot_teleop.png", t_of("teleop turn") + 2)
    shot("lesson14_shot_camera.png", t_of("camera on") + 6)
    shot("lesson14_shot_confirm.png", t_of("confirm shown") - 1)
    y, d = t_of("yes"), t_of("mission done")
    shot("lesson14_shot_pick.png", y + (d - y) * 0.30)
    shot("lesson14_shot_carry.png", y + (d - y) * 0.55)
    shot("lesson14_shot_done.png", d + 3)
    shot("lesson14_shot_answer.png", t_of("chat guide") - 2)
    shot("lesson14_shot_stop.png", t_of("stop button") + 5)


def img_h(f):
    return Image.open(f).size[1]


def gif():
    files = sorted(FRAMES.glob("f*.png"))
    font = ImageFont.truetype(BOLD, 22)
    frames = []
    for i, f in enumerate(files):
        t = i * 2
        text = [n for tt, n in EVENTS if tt <= t]
        img = Image.open(f).convert("RGB").resize((900, round(900 * img_h(f) / 1600)))
        cap = Image.new("RGB", (900, img.height + 40), (20, 20, 20))
        cap.paste(img, (0, 0))
        ImageDraw.Draw(cap).text((12, img.height + 7), CAPTION.get(text[-1] if text else "", "페이지를 연다"), font=font, fill="white")
        frames.append(cap.quantize(colors=128, dither=Image.Dither.NONE))
    frames[0].save(OUT / "lesson14_dashboard.gif", save_all=True, append_images=frames[1:], duration=[250] * (len(frames) - 1) + [2500], loop=0)
    print("saved lesson14_dashboard.gif", len(frames), "frames")


CAPTION = {"page open": "페이지를 연다", "goal info": "장소 버튼 [인포데스크] → Nav2 가 이동", "teleop forward": "수동 조작: 앞으로", "teleop turn": "수동 조작: 제자리 회전",
           "camera on": "카메라 켜기", "chat mission": "LLM 지령: 2번 테이블 손님에게 물 한 잔 가져다 드려", "confirm shown": "단계 목록을 보여 주고 확인을 묻는다",
           "yes": "[진행] → Task Manager 가 단계를 차례로 실행", "mission done": "끝: 결과 문장과 컵 위치 표", "chat question": "질문: 핑크랩은 어떤 회사야?",
           "chat guide": "안내: 약국으로 안내해 줘 (확인 없이 바로 이동)", "stop button": "정지 버튼: 미션과 Nav2 를 멈춘다", "end": "끝"}


if __name__ == "__main__":
    for f in (why, arch, flow, owners, api, shots, gif):
        f()
