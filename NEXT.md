# 다음 세션 재개 안내 (pinklab_robotworld2026)

마지막 갱신: 2026-11-13 저녁 (조명 작업 후 세션 종료, 스택 내려 둠). 이 문서만 보고 이어갈 수 있도록 쓴다.

## 0. 진행 중 (2026-11-15 시작): 강좌 글 19개를 부스 버전으로 다시 만들기 — 다음 세션은 여기부터

사용자 지시: 강좌(`mobile_openarm_ws`, Confluence 3692396550)의 글들과 같은 컨셉 · 같은 내용으로, 이 저장소 코드를 가지고
Confluence **3782936893 "MuJoCo와 ROS2, 2026년 로보월드"** (space 2517565443) 아래에 글을 만든다. 필요하면 다시 캡처 · GIF · 영상.
결정(사용자 답): ① 공통 글 3개(MuJoCo 소개 · URDF→MJCF · 브리지)는 내용 그대로 복사하고 경로 · 명령만 이 저장소에 맞춤(2링크 팔 예제 코드도 복사),
② `lessons/` 실습 코드는 부스 시나리오(컵 · 상담 테이블 · 부스 장소)로 옮겨 새로 만들고 실제로 돌려 확인한 뒤 글을 쓴다, ③ 앞에서부터 하나씩 완성해 바로 게시.

- 글 원본 `docs/camp/*.md` + 그림 스크립트(강좌 `docs/camp/` 에서 복사해 고침). 게시: `set -a; source ../confluence_token.txt; set +a;`
  새 글 `python3 scripts/publish_confluence.py <md> "<제목>" 3782936893 2517565443`, 갱신 `... --update <pageId>`, 비교 `python3 scripts/pull_confluence.py <pageId> <md>`.
- 제목은 space 안에서 유일해야 하므로 강좌 글과 다르게 짓는다 (로보월드 2026 · 부스를 넣음).
- 문서 규칙은 강좌와 같다: 개조식, h3 하나에 그림 하나, 코드 블록 첫 줄에 워크스페이스 기준 경로 주석, 코드 12줄 이하, 설명 3줄 이하.
- 강좌 저장소는 읽기만 한다.

| 순서 | 강좌 글 (md) | 부스 글 | 상태 |
|---|---|---|---|
| 1 | 패키지 소개와 커리큘럼 (intro_curriculum) | 3782281865 | 게시 v1 (그림 22장 부스 내용으로) |
| 2 | 환경 설정과 패키지 사용법 (setup_usage) | 3782936914 | 게시 v2 (도식 20장 + 실제 캡처 8장: install · doctor · env · start · display · high/low · sim_config · viewer:=false) |
| 3 | MuJoCo 소개 (lesson00_mujoco_intro) | 3782281998 | 게시 v1 (그대로 복사, 터미널 그림 2장만 이 저장소 프롬프트로) |
| 4 | URDF에서 MuJoCo 모델로 (lesson01d) | 3782150374 | 게시 v1 (그대로 복사, 터미널 그림 다시 그림) |
| 5 | MuJoCo 브리지 (lesson01e) | 3783002894 | 게시 v1 (그대로 복사, `lessons/01_mujoco_ros2/` 복사 · 이 저장소에서 실행 확인) |
| 6 | 로봇 모델 Description (lesson02) | 3782380144 | 게시 v1 (터미널 그림 10장 실제 실행으로 다시, 도식의 창고 → 부스, '부스 합치기' 절 추가, 요소 수 body 82 · geom 476). Vic Pinky · OpenARM 단독 RViz 캡처와 슬라이더 GIF 는 강좌 것 그대로 |
| 7 | 센서 · TF · Odom (lesson03) | 3782380218 | 게시 v1. 실제 실행으로 다시: drive 화면 · CLI 10종 · TF 트리 · 사각형 실험(한 변 1 m, 출발 `spawn:=5.0,-3.7,0`, 1바퀴 0.3 cm/0.19°, 3바퀴 0.7 cm/0.58°) · 물리 단독(`odom_offline.py`) · spawn:=drinks. 부스는 실시간의 약 0.76배(벽시계 /odom 37.8 Hz, `--use-sim-time` 50.0 Hz). 부스 바닥 윗면은 z = 0.02 m |
| 8 | SLAM (lesson04) | 3783003031 | 게시 v1. 실제 SLAM: `robotworld slam` + `docs/camp/slam_tour.py --record artifacts/dev/slam_maps` (17 지점 약 18 m, 204 s, 막힘 없음) → `artifacts/maps/my_booth.{pgm,yaml}` (641×665, 원점 = 출발 자리 home) · 포즈 그래프(`slam_graph_capture.py`: 노드 553 · 이웃 774 · 먼 엣지 465) · map→odom 0.4 cm. 그림은 SLAM 좌표에 spawn (5.3, -3.2) 을 더해 world 로 그림. teleop 화면은 프로그램 안내문을 그대로 적은 것(직접 실행 안 함) |
| 9 | ROS2 Navigation (lesson05) | 3782282218 | 게시 v1. `robotworld nav moveit:=false` 실제 실행: goal 7.43 -3.77 -1.15 (인포, 15 s) → RViz 2D Goal Pose 끌기(xdotool)로 home 복귀 → 틀린 /initialpose (5.9, -2.8, 23°) 뒤 goal 4.88 -3.02 2.77. 기록 `artifacts/dev/nav_run.pkl` · `nav_amcl.pkl` (`nav_record.py`), 화면 `artifacts/docs/l05_*` · `artifacts/dev/nav_frames/`. 주행 RViz 시점을 부스 가운데로 고침(`warehouse.launch.py` `booth_centre`, Scale 85) |
| 10 | 충돌 회피 (lesson06) | 3782150630 | 게시 v1. 서 있는 관람객(지도에 없는 배우 `worlds/actors_avoid.yaml` 의 `visitor_standing`, `actors:=` 인자로만 켬) + `docs/camp/avoid_scenario.py` (standing: 14.1 s 도착 · 최소 0.54 m / blocked: 90 s 진행 못 해 취소 · 0.87 m 앞 정지 / clear: 20.3 s). 기록 `nav_standing.pkl` · `nav_blocked.pkl`, 화면 프레임 `artifacts/dev/avoid_frames/` (`artifacts/docs/l06_frames.sh`) |
| 11 | 전반부 통합 Demo: 순찰 + 대시보드 (lesson07) | 3782282308 | 게시 v1. `lessons/04_navigation/` 를 부스용으로 옮김 (patrol.py 기본 경로 entrance → classroom_1 → pharmacy → info → home, odom 을 world 로 옮겨 비교 · 대시보드의 안전모 표시 삭제 · odom 보정). 순찰 88 s 성공(AMCL 1.5~5.6 cm). 처음 순서(info → entrance)는 (5.95, -3.54) 모서리에서 Failed to make progress 로 실패 → 3장 '막혔던 곳'으로 씀 (`nav_patrol_stuck.pkl`). 대시보드 화면은 `docs/camp/cdp_capture.py` (headless Chrome) · 세션 스크립트 `artifacts/docs/l07_dash.sh` |
| 12 | MoveIt (lesson08) | 3782150685 | 게시 v1. `robotworld moveit` 실제 실행: arm both ready/hands_up/transport 성공, home 은 강좌와 같이 CONTROL_FAILED(-4). 기록 `arm_ready.pkl` · `arm_home.pkl` (`arm_record.py`), RViz 패널 조작은 xdotool (Goal State (330,539) → hands_up (276,650) → Plan (123,393) → Execute (123,424), Scene Objects 탭 (294,322): 목록은 몇 초 뒤에 채워짐). 로봇 자세 그림 · GIF 는 기록한 관절값의 오프스크린 렌더(`make_task_gifs.py` Replay, 로봇을 home 에 세움) |
| 13 | Arm · End-Effector (lesson09) | 3782380446 | 게시 v1. `lessons/05_moveit/ee_control.py` 복사(명령 이름만 바꿈). `artifacts/docs/l09_cli.sh` 로 전 명령 실행: pose 오차 0.2 mm, cartesian 100 %, 실패 둘(IK 없음 · 53 %), demo 27 s. 기록 `ee_demo.pkl` · `ik_probe.pkl`. 그림의 pose 반복 오차 막대(±0.01 → ±0.001 rad)는 강좌에서 잰 값 그대로 |
| 14 | Pick & Place (lesson10) | 3782282422 | 게시 v1. `lessons/06_pick_place/pick_then_place.py` 를 컵 · 음료대용으로 (`start spawn:=drinks`, pink, 왼팔). 집기 67 s · 놓기 69 s · 슬롯 3.4 cm. 기록 `pick_pink.pkl` (`pick_record.py`; 뒤에 CLI 실행이 이어져 그림에서 첫 실행만 씀). 위치 확인은 TruthLocator(YOLO 안 씀) → 그 절을 새로 씀. 음료대 양옆에 직원이 서 있어 로봇 뒤 위(az 90, el -42)에서 그림 |
| 15 | Navigation + Pick & Place (lesson11) | 3783327838 | 게시 v1. `lessons/07_nav_pick_place/transport.py` (pink → consult_2 213 s · 1.2 cm, blue → consult_1 190 s · 1.2 cm, yellow → consult_1 241 s · 0.7 cm; `artifacts/docs/l11_run.sh`). 기록 `transport_pink.pkl` (330 s 로 잡아야 한 번이 다 들어감). '카메라가 늦을 때' · '고친 것' 두 그림은 강좌 것 그대로(같은 코드의 옛 실패 기록). lessons/07 README 는 명령 이름만 바꿈(내용은 창고 기준 그대로) |
| 16 | LLM + OpenAI API (lesson12) | 3783003247 | 게시 v2. `lessons/08_lmm` 01-04 + `commands_test.yaml`. 60 문장 59/60 × 3 회 (틀림: '팔 내려서 주행 자세로' → ready), 지연 평균 1.0 s, 60 문장 $0.037, 명령 1 회 입력 1396 토큰 (`docs/camp/measure_lesson12_tokens.py`). LLM 이 규칙을 읽고 먼저 거절해서 세계 검증 실패가 안 나옴 → 02 에 API 없는 세계 검증 단계를 추가. 그림 `draw_lesson12_figures.py` · 터미널 `render_lesson12_terminals.py` (로그 `artifacts/docs/l12_*.log` 에서 그림) |
| 17 | LLM → Task Pipeline (lesson13) | 3782380612 | 게시 v1. `lessons/08_lmm` 05-08 + `plans_test.yaml` (20 문장). 계획 18/20 (WorldState 표 없이 부르면 '테이블에 있는 컵' 두 문장을 거절 · 컵 위치를 지어냄). Task Manager 는 `start` 에 포함. 미션 '손님께 음료 가져다 드려 / 2번 테이블 / 응' → 분홍 컵 225 s 성공 (`artifacts/docs/l13_run.sh`, 기록 `mission_text.pkl`, GIF `make_task_gifs.py mission`). 실패 사례: 이미 옮긴 분홍 컵 → 2 단계 pick 'No IK solution', 82 s. 시작 화면 그림은 15 번 것을 그대로 씀. v2 (11-16): 컵 뒤집힘 수정 뒤 다시 기록 (미션 234 s, 실패 사례 84 s) |
| 18 | Web FMS (lesson14) | 3783295186 | 게시 v1. 새로 쓴 글 `docs/camp/lesson14_web_fms.md` (강좌 대시보드 글의 번안이 아님). 실행 `artifacts/docs/l18_fms.sh` (API 로 장소 이동 → 수동 조작 → 카메라 → LLM 미션 → 질문 → 정지, `cdp_capture.py` 2 s 마다 1600x1780 → `artifacts/dev/fms_frames`), 그림 `draw_lesson14_figures.py` (이벤트 시각 `l18_events.log` 로 프레임을 고름) · `render_lesson14_terminals.py` |
| 19 | Final Mission (lesson15) | 3783003446 | 게시 v1. `lessons/10_final_project/01_world_plan.py` (표 없음 3/8 · 표 8/8) · `02_final_mission.py` (시나리오 3 개: 분홍 → 2번 215 s, 음료 한 잔 되묻기 → 파랑 1번 282 s, 분홍 → 음료대 281 s; `artifacts/docs/l15_run.sh`, 기록 `final_mission.pkl`, 운반 중 최대 기울기 4.9°). 그림 `draw_lesson15_figures.py` · `render_lesson15_terminals.py` · GIF `make_task_gifs.py final` |

### 컵 뒤집힘 수정 (2026-11-16, 사용자 지적 → "먼저 고친다")

- 원인: carry 단계가 `hands_up` (관절 이름 자세 `[0,0,0,2,0,0,0]`) 로 가서 손이 위 · 뒤를 향함 → 컵이 155 ~ 161° 뒤집힌 채 운반.
- 고친 것 (`src/warehouse_skills`, `mobile_openarm_description/config/drive_poses.yaml`, SRDF):
  - 새 이름 자세 `carry` (SRDF · drive_poses.yaml): 손 방향이 집을 때와 같고 tcp (0.34, ±0.153, 0.86). x < 0.34 는 IK 가 없음. `skills.yaml` `carry_pose: carry` · `carry_tcp`.
  - `do_pick`: 운반점까지 Cartesian 직선 → `move_named(carry)` (브리지는 주행 자세일 때만 /cmd_vel 을 받으므로 관절값을 정확히 맞춤).
  - `moveit_client.py`: `ik_solutions` · `plan_cartesian` · `move_pose_then_cartesian` (IK 해마다 직선 경로를 먼저 계획해 보고 되는 해로만 이동. `then` = 잡은 뒤 운반점까지 이어지는 해 우선). grasp · place 가 이것을 씀.
  - `dock.target_dx` 0.47 → 0.43: 0.47 에서는 가운데 컵이 팔 길이의 97 % → 직선 경로가 끊김. 계획만으로 비교한 결과 (충돌 무시): 로봇을 5 ~ 15 cm 올리면 더 나빠짐, 5 ~ 10 cm 내리거나 4 cm 가깝게 도킹하면 전 자리 가능. (사용자가 "높이를 올리는 것도 고려" 라고 했으나 측정 결과 반대 방향이라 도킹 거리만 바꿈 → 사용자에게 보고할 것)
  - 후퇴점은 운반점보다 몸 쪽으로 가지 않게 제한, 놓은 뒤 후퇴 실패는 실패로 치지 않음, 잡기 전/놓은 뒤 실패 시 팔을 transport 로 되돌림 (안 그러면 다음 goal 이 navigation timed out).
- 결과: 분홍 · 파랑 · 노랑 배달 모두 성공, 운반 중 최대 기울기 4.9° · 5.1° · 3.9° (`artifacts/dev/transport_all.pkl`). 14 · 15 · 17 번 그림 · GIF · 본문을 다시 만들어 게시 (v2). 다시 돌린 스크립트 `artifacts/docs/recapture4.sh`, 고치기 전 로그 `artifacts/docs/before_carry_fix/`.
- 주의: `pkill -f` / `pgrep -f` 패턴은 heredoc 본문과 같은 줄의 파일 이름에도 걸린다 (셸이 죽어 exit 144).
- Final Mission 실행 중 발견 (11-16): Nav2 goal 직후 (베이스 감속 중) 팔 궤적을 보내면 브리지가 거부 (`actions.py goal`: twist > 0.04) → `MoveIt joint motion failed (error_code=-4)`. 팔이 transport 자세의 허용 오차 경계 (0.00099 rad) 에 있으면 작은 궤적이 생겨서 걸림. `do_pick` 첫머리 `nav.settle()` + `move_joints` 가 CONTROL_FAILED 를 1.5 s 뒤 한 번 재시도.
- 컵 위치표 규칙 (`world.py prompt()`) 에 두 줄 추가: '~로 다시 가져와/돌려놔/치워 줘' 의 '~로' 는 도착지 · '원래 자리' = 음료대 / 테이블이 문장에 없으면 표를 보고 고르지 말고 되묻기. `01_world_plan.py`: 표 없음 3/8, 처음 규칙 6/8, 최종 8/8 × 3 회.

작업 요령 (2026-11-15):
- 그림 스크립트는 `docs/camp/` (강좌 것을 복사해 부스 내용으로 고침). 도식: `python docs/camp/draw_intro_figures.py` · `draw_architecture.py` · `draw_setup_figures.py` · `draw_setup_detail_figures.py`.
  mujoco 를 쓰는 그림은 `./scripts/robotworld exec env MUJOCO_GL=egl python3 docs/camp/draw_setup_lowspec_figures.py` (bridge.py 가 rclpy 를 import 하므로 wrapper 환경에서).
- 터미널 그림은 실제 로그로: `artifacts/docs/*.log` → `python docs/camp/render_setup_terminals.py`. `render_terminal.py` 의 프롬프트는 `pw@laptop:~/pinklab_robotworld2026$`. ✅ 는 글꼴에 없어 `[OK]` 로 바꿔 그림.
- 화면 캡처: 스택을 띄우고 `xdotool search --name "MuJoCo : mobile"` / `"pinklab_robotworld2026/artifacts/mobile"`(RViz) 로 창을 찾아 `windowsize` · `windowmove` · `windowactivate` 뒤 `import -window <id>`. 창을 닫거나 최소화하지 않는다. 끝나면 `./scripts/robotworld stop`.
- 오프스크린 렌더에서 로봇을 시작 위치에 세우려면 `adr = model.joint("floating_base").qposadr[0]; data.qpos[adr:adr+2] = [5.3, -3.2]` (저장된 모델에서는 로봇이 원점에 있다).
- 게시 중 Confluence 가 가끔 HTTP 500 을 낸다(본문은 반영, 그림 첨부가 끊김) → 같은 명령을 한 번 더.
- 코드 발췌가 이 저장소 소스와 맞는지: 강좌와 다른 파일은 `mobile_openarm_mujoco/model.py`(build_model 의 월드 부분) · `bridge.py` · `warehouse.launch.py` 뿐 (`diff ../mobile_openarm_ws/<파일> <파일>` 로 확인).
- zsh 에서 `R="./scripts/robotworld exec"; $R ros2 ...` 는 한 단어로 읽혀 실패 → CLI 묶음은 bash 스크립트 파일로 (`artifacts/docs/l02_cli.sh`).
- 7번 글 도구: `artifacts/docs/l03_cli.sh` · `l03_hz.sh` · `l03_measure.py`(접촉 깊이 · 직진/회전 비율) → `docs/camp/render_lesson03_terminals.py` · `draw_lesson03_square.py` · `make_nav_gifs.py square` · `draw_lesson03_figures.py` · `draw_lesson03_drift_figures.py`. `odom_experiment.py` 는 truth 를 출발 자세 기준으로 기록하게 고침. view_frames 의 pdf 는 작업 공간 맨 위에 생긴다(wrapper 가 cd 함).
- RViz(1280x900 창)의 지도 영역은 x 364~1264, y 62~868 px, 가운데 = world (4.5, -3.0), 85 px/m → world (x, y) 의 픽셀 = (814 + 85·(x − 4.5), 465 − 85·(y + 3.0)). 2D Goal Pose: `xdotool mousemove --window $R 485 43 click 1` 뒤 그 픽셀에서 mousedown → 방향으로 끌고 mouseup.
- 기록기를 두 번 겹쳐 돌리면 앞 기록에 뒤 실험이 섞인다(9번 글에서 겪음: 그림 쪽에서 셋째 목표를 잘라 냄).
- `pkill -f` / `pgrep -f` 패턴이 같은 Bash 호출 안의 heredoc 글자에도 걸려 셸이 죽는다(11번 글에서 겪음) → `pkill -f "cdp_captur[e]"` 처럼 쓰고, 그 문자열이 든 스크립트를 같은 호출에서 만들지 않는다.
- `ros2 topic echo --once /patrol/status` 는 patrol.py 가 도는 동안에만 값이 나온다.
- 뷰어 시작 시점을 부스 가운데로 고침(`bridge.py`: lookat = spawn, distance = 1.5 × 부스 긴 변, azimuth 120, elevation -45). 환경 설정 글의 start 캡처는 1.2 배일 때 찍은 것.

같은 날 한 일: `sim_config.yaml` 사양 두 단계 `high`(지금까지 쓰던 설정) · `low`(뷰어 로봇 단순 형상 · 카메라 그림자 끔 · RViz 10 FPS).
`bridge.py` `show_simple_meshes` 는 로봇 메시만 바꾼다(부스 간판 메시는 그대로). `./scripts/robotworld start profile:=low` 로 실행 확인. 커밋 안 함.

## 상태 한눈에

- GitHub: https://github.com/PinkWink/pinklab_robotworld2026 (public). 2026-11-13 bd86af1 로 로봇 스택 · FMS · 영상 스크립트 · 조명까지 전부 push (소스 약 146 MB).
- 강좌 저장소(`/home/pw/mujoco_ros2/mobile_openarm_ws`)는 이 작업으로 바뀐 것 없음 (마지막 8242823, 깨끗함). 강좌 코드는 읽기만 한다.

## 실행

```bash
cd ~/mujoco_ros2/pinklab_robotworld2026
./scripts/robotworld start      # MuJoCo 부스 + 로봇 + Nav2 + MoveIt + PickPlace + Task Manager (도메인 44)
./scripts/robotworld fms        # 다른 터미널: http://localhost:8080
./scripts/robotworld stop
./scripts/robotworld pick pink drinks consult_2      # 명령줄 컵 옮기기
```
- `.venv` 는 `--system-site-packages` 로 만들었고 `requirements.txt` 설치 + `scipy`, `PyYAML`. `.env` 에 OpenAI 키(강좌 `.env` 에서 복사, git 제외).
- 녹화 중에는 MuJoCo 창을 닫지 말 것: 창을 닫으면 브리지가 정상 종료하고 launch 가 스택 전체를 내린다.
- 셸에서 `pkill -f "fms/server.py"` 처럼 쓰면 같은 문자열이 든 내 셸도 죽는다 → `pkill -f "[f]ms/server.py"` 로, 그리고 그 문자열을 다른 코드와 한 명령에 섞지 말 것.

## 한 일 (이번 세션)

1. 부스 월드(`src/robotworld`): 설계 HTML 의 `window.BOOTH` → MJCF. S자 간판은 한 덩어리 메시 + 곡면 로고, 원기둥 배너(흰 기둥 + 분홍 원통에 세로 "PinkLAB Studio"),
   주변 부스는 0.5 m 로 낮춤, 부스 조명 6개 + 밝은 headlight. `booth/scenario.yaml`: 상담 테이블 의자 1개씩 + 손님, 음료대, '숫자로 보는 실적' 문구(200+ · 2,000+ · 100+ · 5년차).
2. 강좌 패키지를 `git archive` 로 복사해 수정(패키지 이름 유지, 도메인 44): 브리지가 부스 병합(`mjcf_world: robotworld`), 원기둥 물체, 스테이션 프레임(가장자리 · 방향 · 높이)으로
   PickPlace 일반화, 컵 3개, 장소 12곳(`warehouse_lecture/worlds/locations.yaml`), 모델 형상으로 만든 Nav2 지도(`scripts/generate_booth_map.py`), MoveIt 장애물(`booth.yaml scene`),
   부스용 LLM 프롬프트 · 컵/손님 표(`commands/plan_parser.py`, `world.py`), Task Manager 를 launch 에 포함, doctor · install 정리.
3. 웹 FMS(`fms/`): 지도 · Nav2 클릭 이동 · 수동 조작(데드맨 0.4 s) · 카메라(평소 꺼짐, frame_tap 플래그 파일) · LLM 대화(계획 → 확인 → ExecutePlan) · 정지.
4. 검증: 명령줄 배달 231 s 성공, FMS 경유 LLM 배달 성공(노란 컵 / 분홍 컵 → 2번 테이블), 안내 지령 성공. 인포 정지 자리는 여유 0.76 m 자리로 옮김(옛 자리에서 갇힘).
   - 2026-11-13 조명: 부스 조명 6개 → 부스 바로 위 16 m 의 좁은 스포트 1개(`booth_key`, 그림자) + 홀 조명 · headlight 약간 낮춤.
     설계 HTML 의 간판 조명 기구(일자 간판 3개 · 물결 간판 5개)를 넣고, PinkLAB 글자 쪽 5개(일자 3 + 물결 로고 양옆 2)만 짧은 스포트로 켬.
     MuJoCo 는 조명 8개까지(headlight 포함)만 그리므로 지금 7 + headlight = 8, 더 넣을 자리 없음.
     주변 부스 윗면 깜빡임 = 블록 윗면과 테두리 띠 윗면이 같은 높이(z-fighting) → 블록을 4 mm 올림.
     `booth_key` 는 그림자 끔(16 m 스포트 그림자는 로봇 씬의 1 cm znear 에서 점무늬). 조명이 어두워지자 hall_sun 그림자의 점무늬(shadow acne)가
     흰 바닥에 드러나 `model.py` 에서 부스일 때 `shadowclip=3` (기본 1 x extent 9 m 는 텍셀이 너무 잘아 고정 bias 미만). 영상 두 개 새 조명으로 다시 렌더.
     같은 날 2차: 간판 조명을 넓은 투광(flood)으로 — 일자 간판 1 (2.4 m 앞) · 물결 로고 양옆 2 · 뒷벽(외벽 바깥 분홍 면) 2 + 뒷벽 조명 기구 4개.
     조명 8개 한도는 headlight 포함으로 실측 확인(headlight active=0 이면 한 자리 비지만, 빛 반대쪽 면이 새까매져서 켜 둠).
     조명을 바꾸면 영상 전에 `artifacts/mobile_generated/warehouse.xml` 을 다시 만들 것(스택을 한 번 띄우거나 build_model(…, robot.urdf)).
5. 소개 영상(`video/`): `record.py`(상태 기록) · `browser_capture.py`(FMS 화면 + 시각) · `replay.py`(오프라인 재렌더) · `compose.py`(본편) · `orbit.py`(부스 일주).
   결과물 `artifacts/video/pinklab_robotworld2026_intro.mp4`(1:45) · `pinklab_booth_orbit.mp4`(20 s) · `youtube.txt`(제목 · 설명 · 챕터). 소리 없음.
   녹화 데이터 `artifacts/video/run.pkl` · `browser/` · `chat.json` 이 있으면 `compose.py` 만 다시 돌려 고칠 수 있다(약 3분).

## 다음 (사용자 결정 대기)

- 영상 두 개(`artifacts/video/` intro 1:45 · orbit 20 s)는 2026-11-13 최종 조명으로 다시 렌더함(git 밖). 조명을 또 바꾸면 스택을 한 번 띄워 `artifacts/mobile_generated/warehouse.xml` 을 새로 만든 뒤 `orbit.py` · `compose.py` 재실행.
- 조명 밝기 조정 요청이 오면 `src/robotworld/robotworld/world.py` `lights()` 의 flood 인자(out · up · cutoff · diffuse). 조명은 이미 8개 한도(7 + headlight).
- 영상 수정 요청이 오면 `video/compose.py` (자막 · 장면 길이 · 배속 · 카메라).
- Confluence 번외편 페이지(부모 3692396550 아래) — 아직 안 만듦.
- 라이선스 파일 여부.
- 알려진 한계: 수동 조작으로 테이블 · 사람에 바짝 붙이면 Nav2 가 회전을 충돌로 보고 못 빠져나옴, 부스 사람은 움직이지 않음, `commands/parser.py`(단일 명령 파서) 프롬프트는 아직 창고 내용.
