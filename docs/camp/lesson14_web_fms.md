## 1. 브라우저 한 화면에서 보고 · 움직이고 · 시키기

### 웹 FMS 가 하는 일

![보기 · 움직이기 · 시키기](lesson14_why.png){width=1000}

### 화면 구성

![부스 지도 · 로봇 상태 · 수동 조작 · 장소로 이동 · 카메라 · LLM 지령](lesson14_layout.png){width=1000}

### 통신 구조

![브라우저 ↔ fms/server.py (Flask + rclpy 노드) ↔ Nav2 · Task Manager · 시뮬레이터](lesson14_arch.png){width=1000}

### HTTP API

![주소와 하는 일](lesson14_api.png){width=1000}

### /cmd_vel 을 쓰는 세 가지

![수동 조작 · Nav2 goal · LLM 미션의 우선순위](lesson14_owners.png){width=1000}

### LLM 지령 한 건의 흐름

![POST → 작업 스레드 → 대화 관리 → 확인 → ExecutePlan → 결과](lesson14_sequence.png){width=1000}

## 2. 실행

### 터미널 1: 시뮬레이터

```bash
cd ~/pinklab_robotworld2026
./scripts/robotworld start     # 시뮬레이터 · Nav2 · MoveIt · PickPlace 서버 · Task Manager
```

### 터미널 2: FMS 서버

```bash
cd ~/pinklab_robotworld2026
./scripts/robotworld fms       # 브라우저에서 http://localhost:8080
# 다른 PC · 태블릿에서 보려면: ./scripts/robotworld fms --host 0.0.0.0
```

### 실행 결과: 터미널 2

![FMS 서버 출력](lesson14_t2.png){width=1000}

### 실행 결과: 장소 버튼으로 이동

![인포데스크 버튼 → Nav2 경로와 남은 거리](lesson14_shot_goal.png){width=1000}

### 실행 결과: 수동 조작

![누르는 동안만 움직임: 앞으로 → 제자리 회전](lesson14_shot_teleop.png){width=1000}

### 실행 결과: 카메라 켜기

![머리 카메라 영상 (켰을 때만 JPEG 를 만든다)](lesson14_shot_camera.png){width=1000}

### 실행 결과: LLM 지령 → 확인

![단계 목록 · 위 계획대로 진행할까요?](lesson14_shot_confirm.png){width=1000}

### 실행 결과: 집기

![2/4 단계: 음료대에서 분홍 컵 집기](lesson14_shot_pick.png){width=1000}

### 실행 결과: 운반 · 놓기

![4/4 단계: 2번 상담 테이블 앞](lesson14_shot_carry.png){width=1000}

### 실행 결과: 완료

![결과 문장 · 컵 위치 표가 바뀜](lesson14_shot_done.png){width=1000}

### 실행 결과: 질문에 답하기

![핑크랩은 어떤 회사야? (로봇은 움직이지 않는다)](lesson14_shot_answer.png){width=1000}

### 실행 결과: 정지 버튼

![약국으로 안내 중 정지: 미션 중지 · 취소했습니다](lesson14_shot_stop.png){width=1000}

### 움직이는 그림: 한 번의 실행 전체

![웹 FMS (움직이는 그림)](lesson14_dashboard.gif){width=900}

## 3. 코드

### 상태 한 곳에 모으기 - server.py Fms.__init__ 발췌

```python
# fms/server.py
class Fms(Node):
    def __init__(self):
        super().__init__("robotworld_fms", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.lock = threading.Lock()
        self.s = dict(pose=None, cov=None, twist=[0.0, 0.0], plan=[], scan=[], cups={},
                      nav=dict(state="대기", goal=None, remaining=None),
                      mission=dict(active=False, step=0, total=0, action="", detail="", steps=[]),
                      pending=False, busy=False, chat=[], camera=False)
```

- `self.s` = 브라우저에 보낼 상태 전체 · ROS 콜백이 쓰고 Flask 가 읽음
- 쓰는 쪽 · 읽는 쪽이 다른 스레드 → 잠금 (`lock`) 하나로 보호

### 토픽 → 상태 - server.py on_amcl · on_plan

```python
# fms/server.py
def put(self, **kw):
    with self.lock:
        self.s.update(kw)

def on_amcl(self, m):
    p, c = m.pose.pose, m.pose.covariance
    self.put(pose=[round(p.position.x, 3), round(p.position.y, 3), round(yaw_of(p.orientation), 3)],
             cov=[round(math.sqrt(max(c[0], 0)), 3), round(math.sqrt(max(c[7], 0)), 3)])

def on_plan(self, m):
    self.put(plan=[[round(p.pose.position.x, 2), round(p.pose.position.y, 2)] for p in m.poses[::3]])
```

- 콜백은 메시지에서 필요한 숫자만 뽑아 `put()` · 경로는 3 점마다 하나만 보냄
- 같은 방식: `/odom` → `twist` · `/scan` → 지도 좌표의 점들 · 컵 자세 → `cups`

### 상태 흘려보내기 (SSE) - server.py /api/stream

```python
# fms/server.py make_app
@app.get("/api/stream")
def stream():
    def gen():
        while True:
            yield f"data: {json.dumps(fms.snapshot(), ensure_ascii=False)}\n\n"
            time.sleep(0.2)
    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})
```

- Server-Sent Events: 응답을 끝내지 않고 `data: ...` 줄을 0.2 s 마다 계속 보냄
- 브라우저가 묻지 않아도 서버가 밀어 줌 · 방향은 서버 → 브라우저 한쪽뿐

### 브라우저: 상태 받기 - app.js connect

```javascript
// fms/static/app.js
function connect() {
  const es = new EventSource("/api/stream");
  es.onopen = () => { $("conn").textContent = "연결됨"; $("conn").classList.remove("off"); };
  es.onerror = () => { $("conn").textContent = "끊김"; $("conn").classList.add("off"); };
  es.onmessage = (ev) => { state = JSON.parse(ev.data); update(); };
}
```

- `EventSource` 는 끊기면 스스로 다시 연결함
- 메시지마다 `state` 를 통째로 바꾸고 `update()` 가 화면을 다시 그림

### 수동 조작: dead-man - server.py drive · teleop_tick

```python
# fms/server.py
def drive(self, v, w):
    if not self.teleop_active:
        self.cancel_all("수동 조작")                   # Nav2 goal · 미션을 먼저 취소
    self.teleop = (max(-0.3, min(0.3, v)), max(-0.8, min(0.8, w)), time.time())

def teleop_tick(self):                                 # 0.1 s 타이머
    v, w, t = self.teleop
    if time.time() - t < 0.4:
        self.teleop_active = True
        self.cmd_vel.publish(Twist(linear=Vector3(x=float(v)), angular=Vector3(z=float(w))))
    elif self.teleop_active:                           # 손을 뗌: 0 을 한 번 보내고 조용히
        self.teleop_active = False
        self.cmd_vel.publish(Twist())
```

- 요청이 0.4 s 안에 다시 오지 않으면 정지 → 탭을 닫거나 연결이 끊겨도 로봇이 섬
- 속도는 서버에서 한 번 더 제한 (0.3 m/s · 0.8 rad/s)
- `Twist(...)` 한 줄은 발췌에서 줄여 쓴 것 (실제 코드는 `msg.linear.x` · `msg.angular.z` 에 대입)

### 브라우저: 누르는 동안 보내기 - app.js startDrive

```javascript
// fms/static/app.js
function startDrive(v, w) {
  driveDir = [v, w];
  if (driveTimer) return;
  const tick = () => { const spd = +$("spd").value; post("/api/drive", { v: driveDir[0] * spd, w: driveDir[1] * Math.min(0.6, spd * 4) }); };
  tick(); driveTimer = setInterval(tick, 150);
}
function stopDrive() { clearInterval(driveTimer); driveTimer = null; ... }
```

- 버튼을 누르면 150 ms 마다 `/api/drive` · 떼면 타이머만 멈춤 (정지 명령을 따로 보내지 않음)
- 슬라이더 값이 직진 속도 · 회전은 그 4 배 (최대 0.6 rad/s)

### 지도 클릭 → Nav2 goal - server.py go_to 발췌

```python
# fms/server.py
def go_to(self, x, y, yaw, label=""):
    if self.s["busy"]:
        raise RuntimeError("미션 실행 중에는 이동 명령을 보낼 수 없습니다 (먼저 중지)")
    self.cancel_nav()                                   # 앞 goal 취소
    goal = NavigateToPose.Goal()
    goal.pose.header.frame_id = "map"
    goal.pose.pose.position.x, goal.pose.pose.position.y = float(x), float(y)
    goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
    self.nav.send_goal_async(goal, feedback_callback=on_fb).add_done_callback(on_accept)
```

- 장소 버튼은 `locations.yaml` 의 `base_goal` 을, 지도 클릭은 클릭한 좌표를 그대로 보냄
- 피드백 (`distance_remaining`) 은 `nav.remaining` 에, 결과는 채팅 줄 (`도착` · `취소됨`) 로 남김

### LLM 지령 받기 - server.py Fms.chat 발췌

```python
# fms/server.py
def chat(self, text):
    self.say("사용자", text, "user")
    if not self.chat_lock.acquire(blocking=False):      # 앞 문장을 처리 중
        self.say("시스템", "앞 문장을 처리 중입니다. 끝난 뒤에 다시 말씀해 주세요.", "warn")
        return
    try:
        if self.dialog is None:
            self.dialog = PlanDialogManager(PlanParser(), executor=self.execute_plan,
                                            speak=lambda t: self.say("로봇", t, "reply"), world=self.world_state)
        self.dialog.handle(text)
    except Exception as error:                          # LLM · 네트워크 · ROS 오류를 채팅에 표시
        self.say("시스템", f"오류: {error}", "error")
```

- 앞 글의 `PlanDialogManager` 를 그대로 씀 · `speak` 만 채팅 기록으로, `executor` 만 `/execute_plan` 호출로 바꿈
- `world=self.world_state`: 컵 위치 표가 프롬프트에 들어감 → 실행이 끝나면 표를 고침
- `/api/chat` 은 이 함수를 새 스레드에서 부르고 바로 응답 → LLM 을 기다리는 동안에도 화면이 멈추지 않음

### 계획 실행과 진행 표시 - server.py execute_plan 발췌

```python
# fms/server.py
def on_fb(m):
    f = m.feedback
    with self.lock:
        self.s["mission"].update(step=int(f.step), total=int(f.total), action=f.action, detail=f"{f.phase}: {f.detail}")
    if f.phase == "start":
        self.say("로봇", f"[{f.step + 1}/{f.total}] {f.detail}", "step")

self.plan_client.send_goal_async(plan.to_msg(text), feedback_callback=on_fb).add_done_callback(on_accept)
done.wait()                                             # 대화 스레드는 결과를 기다림
```

- Task Manager 의 피드백이 `mission` (단계 번호 · 세부) 과 채팅의 `[2/4] 분홍 컵 집기` 줄이 됨
- `done` = `threading.Event` · 결과 콜백이 `set()` 하면 대화 스레드가 깨어나 결과 문장을 말함

### 정지 - server.py cancel_all

```python
# fms/server.py
def cancel_all(self, why=""):
    if self.nav_handle is not None:
        self.cancel_nav()
        with self.lock:
            self.s["nav"]["state"] = "취소됨"
    if self.plan_handle is not None:
        self.plan_handle.cancel_goal_async()            # Task Manager → PickPlace · Nav2 까지 취소가 내려감
        if why:
            self.say("시스템", f"미션 중지 ({why})", "mission")
```

- 정지 버튼 (`/api/stop`) · 수동 조작의 첫 요청이 이 함수를 부름
- FMS 가 직접 보낸 Nav2 goal 과 Task Manager 의 계획을 따로 기억해 둘 다 취소

### 카메라: 켰을 때만 - frame_tap.py FmsPipeline 발췌

```python
# fms/frame_tap.py
def __call__(self, frames):
    super().__call__(frames)                         # 도킹용 마커 검출은 항상
    if not (FRAMES / "enabled").exists():            # 브라우저가 켜지 않았으면 여기서 끝
        return
    for name, frame in frames.items():
        ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
        tmp = FRAMES / f".{name}.jpg.tmp"
        tmp.write_bytes(jpg.tobytes())
        os.replace(tmp, FRAMES / f"{name}.jpg")       # 원자적 교체: 서버가 반쪽 파일을 읽지 않음
```

- 시뮬레이터 안의 카메라 핸들러 · `/dev/shm/robotworld_fms/enabled` 파일이 있을 때만 JPEG 저장
- 서버는 그 파일을 MJPEG (`/camera/head_camera.mjpg`) 로 흘려보냄 → 영상이 ROS 토픽을 거치지 않음

### 해 볼 것

- 지도에서 한 점을 누른 채 끌어 도착 방향을 정해 보기 (끈 방향을 보고 멈춤)
- 미션 실행 중에 장소 버튼을 눌러 409 오류 문장이 채팅에 뜨는지 보기
- "흰 옷 입은 손님한테 파란 컵 갖다 드려" → 손님 설명으로 테이블을 고르는지, 끝난 뒤 컵 표가 바뀌는지 보기
