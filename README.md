# PinkLAB @ 로보월드 2026 — MuJoCo 부스

로보월드 2026(KINTEX 3홀 A03) 핑크랩 부스를 MuJoCo 로 옮긴 번외편 저장소입니다.
이 부스 안에서 로봇이 물건을 옮기고 관람객을 안내하는 시나리오를 만들어 갑니다.

강좌 저장소([pinklab_mobile_openarm_ros2_mujoco](https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco))와는 완전히 별개입니다. 강좌 코드는 쓰지도 고치지도 않습니다.

## 지금 단계: 부스 월드

- 부스 9 × 6 m, 높이 4.5 m의 4면 오픈 구조와 주변 부스·홀 벽
- 벽·창고·낮은 벽·기둥·상부 S자 간판(원형 기둥 1개)·일자 간판
- 교실1·교실2·약국·상담존·모방학습존·인포데스크의 집기, 양팔로봇(PL-2M) 전시 2대
- 벽 그래픽: 로고, 슬로건, 실적, 커리큘럼, 연혁, 약국 선반, QR, 모니터 화면
- 스태프 10명, 관람객 12명. mocap 바디라서 다음 단계에서 움직일 수 있습니다.
- 설계 파일의 7개 시점이 이름 있는 카메라로 들어 있습니다: bird1 · main1 · main2 · north · west · studio · top

## 실행

```bash
sudo apt install fonts-nanum                 # 벽 그래픽의 한글
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/view_world.py       # MuJoCo 뷰어 (Rendering → Camera 에서 시점 선택)
MUJOCO_GL=egl .venv/bin/python scripts/render_views.py   # build/views/<시점>.png
```

`scripts/build_world.py` 는 `build/booth.xml` 과 `build/textures/*.png` 만 만듭니다.

## 구성

| 경로 | 내용 |
|---|---|
| `booth/booth_data.json` | 부스 설계 데이터. 설계 HTML의 `window.BOOTH` 를 그대로 옮긴 것(최종 평면도 2026-10-14) |
| `booth/images/` | 설계 HTML에 들어 있던 그래픽·로고·모니터 화면·QR |
| `booth/floorplan.png` | 평면도 (FLOOR PLAN 1/50 재작도) |
| `robotworld/world.py` | 설계 데이터를 MJCF 로 바꾸는 빌더 |
| `robotworld/textures.py` | 벽 그래픽을 Pillow 로 그리기 |
| `tools/extract_booth_html.py` | 설계 HTML이 바뀌면 `booth/` 를 다시 뽑기 (node 필요) |

## 좌표

- 설계 데이터의 단위는 평면 cm, 높이 m 입니다. 부스 왼쪽 위 모서리가 (0, 0)이고, x는 메인 통로 쪽, z는 주출입구 쪽입니다.
- MuJoCo 좌표는 X = x / 100, Y = −z / 100, Z = 높이입니다. 그래서 부스는 X 0 ~ 9, Y −6 ~ 0 에 놓이고, 메인 통로는 +X, 주출입구는 −Y 쪽입니다.
- 설계의 각도 `ang`(평면도에서 시계 방향)는 MuJoCo yaw = −ang 입니다.

## 다음 단계

1. 모바일 양팔로봇 모델과 MuJoCo–ROS 2 브리지를 이 저장소로 옮겨 독립시키기
2. 부스 지도 작성과 Nav2 주행
3. 물건 옮기기(약국 · 픽앤플레이스 테이블)와 관람객 안내(인포 → 각 존)
