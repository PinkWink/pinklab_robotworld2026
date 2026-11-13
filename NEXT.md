# 다음 세션 재개 안내 (pinklab_robotworld2026)

마지막 갱신: 2026-11-13 저녁 (조명 작업 후 세션 종료, 스택 내려 둠). 이 문서만 보고 이어갈 수 있도록 쓴다.

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
