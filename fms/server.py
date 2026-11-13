"""PinkLAB RobotWorld 2026 FMS: one web page to watch and command the booth robot.

    ./scripts/robotworld fms                       # http://localhost:8080  (after ./scripts/robotworld start)
    ./scripts/robotworld fms --host 0.0.0.0        # open it to other PCs / tablets on the network

Functions
  map       booth map (/map), robot pose (AMCL), Nav2 path, lidar points, cups, named places
  drive     hold-to-drive buttons / WASD keys -> /cmd_vel (dead-man 0.4 s; cancels Nav2 and missions first)
  navigate  click (and drag for the heading) on the map, or a place button -> Nav2 NavigateToPose
  camera    off by default; when switched on the simulator writes JPEGs (fms/frame_tap.py) and this server streams MJPEG
  LLM       a sentence -> booth planner (plan / ask back / answer) -> confirm -> Task Manager (/execute_plan),
            progress and the robot's result sentence in the chat; the cup table is updated after each mission

One process: an rclpy node spun in a background thread keeps the latest state; Flask serves the page, a
Server-Sent Events stream of that state (5 Hz) and small JSON commands. The browser never talks ROS.
"""
import argparse
import json
import math
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from action_msgs.msg import GoalStatus
from flask import Flask, Response, jsonify, request, send_from_directory
from geometry_msgs.msg import PoseArray, PoseWithCovarianceStamped, Twist
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid, Odometry, Path as NavPath
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener
from warehouse_interfaces.action import ExecutePlan

from mobile_openarm_mujoco.model import load_world
from warehouse_lecture.commands.dialog import PlanDialogManager
from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.commands.schema import PLACE_KO, TARGET_KO
from warehouse_lecture.commands.world import WorldState
from warehouse_lecture.memory.locations import Locations

HERE = Path(__file__).parent
FRAMES = Path(os.environ.get("ROBOTWORLD_FRAMES", "/dev/shm/robotworld_fms"))   # written by frame_tap.py
LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
NAV_STATUS = {GoalStatus.STATUS_SUCCEEDED: "도착", GoalStatus.STATUS_ABORTED: "실패", GoalStatus.STATUS_CANCELED: "취소됨"}


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class Fms(Node):
    """Latest robot state + the actions the page can start. Callbacks write under one lock, Flask reads snapshots."""

    def __init__(self):
        super().__init__("robotworld_fms", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.lock = threading.Lock()
        self.group = ReentrantCallbackGroup()
        self.s = dict(pose=None, cov=None, twist=[0.0, 0.0], plan=[], scan=[], cups={},
                      nav=dict(state="대기", goal=None, remaining=None),
                      mission=dict(active=False, step=0, total=0, action="", detail="", steps=[]),
                      pending=False, busy=False, chat=[], camera=False)
        self.map_png, self.map_meta = None, None
        self.world = load_world()
        self.cup_names = [o["name"] for o in self.world["objects"]]
        self.locations = Locations()
        self.tf = Buffer()
        TransformListener(self.tf, self)
        self.cmd_vel = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self.on_amcl, LATCHED)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_subscription(NavPath, "/plan", self.on_plan, 10)
        self.create_subscription(LaserScan, "/scan", self.on_scan, qos_profile_sensor_data)
        self.create_subscription(OccupancyGrid, "/map", self.on_map, LATCHED)
        self.create_subscription(PoseArray, "/warehouse/object_poses", self.on_cups, 10)
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose", callback_group=self.group)
        self.plan_client = ActionClient(self, ExecutePlan, "/execute_plan", callback_group=self.group)
        self.nav_handle = self.plan_handle = None
        self.teleop = (0.0, 0.0, 0.0)          # v, w, wall time of the last request
        self.teleop_active = False
        self.create_timer(0.1, self.teleop_tick, callback_group=self.group)
        # LLM: planner + dialog (clarify / confirm / execute) + what the robot believes about the cups
        self.world_state = WorldState()
        self.dialog = None                     # created lazily: needs OPENAI_API_KEY
        self.chat_lock = threading.Lock()
        self.set_camera(False)

    # ------------------------------------------------------------------ subscriptions
    def put(self, **kw):
        with self.lock:
            self.s.update(kw)

    def on_amcl(self, m):
        p, c = m.pose.pose, m.pose.covariance
        self.put(pose=[round(p.position.x, 3), round(p.position.y, 3), round(yaw_of(p.orientation), 3)],
                 cov=[round(math.sqrt(max(c[0], 0)), 3), round(math.sqrt(max(c[7], 0)), 3)])

    def on_odom(self, m):
        self.put(twist=[round(m.twist.twist.linear.x, 2), round(m.twist.twist.angular.z, 2)])

    def on_plan(self, m):
        self.put(plan=[[round(p.pose.position.x, 2), round(p.pose.position.y, 2)] for p in m.poses[::3]])

    def on_scan(self, m):
        try:
            t = self.tf.lookup_transform("map", m.header.frame_id, Time.from_msg(m.header.stamp))
        except Exception:
            return
        yaw, o = yaw_of(t.transform.rotation), t.transform.translation
        r = np.asarray(m.ranges)[::3]
        a = m.angle_min + np.arange(len(m.ranges))[::3] * m.angle_increment
        ok = np.isfinite(r) & (r < 8.0)
        x, y = o.x + r[ok] * np.cos(a[ok] + yaw), o.y + r[ok] * np.sin(a[ok] + yaw)
        self.put(scan=np.round(np.c_[x, y], 2).tolist())

    def on_map(self, m):
        h, w = m.info.height, m.info.width
        d = np.array(m.data, dtype=np.int16).reshape(h, w)
        img = np.where(d < 0, 205, np.where(d >= 65, 0, 254)).astype(np.uint8)[::-1]     # row 0 = top = max y
        ok, png = cv2.imencode(".png", img)
        with self.lock:
            self.map_png = png.tobytes()
            self.map_meta = dict(resolution=m.info.resolution, width=w, height=h,
                                 origin=[m.info.origin.position.x, m.info.origin.position.y], version=time.time())

    def on_cups(self, m):
        if len(m.poses) == len(self.cup_names):
            self.put(cups={n: [round(p.position.x, 3), round(p.position.y, 3), round(p.position.z, 3)] for n, p in zip(self.cup_names, m.poses)})

    # ------------------------------------------------------------------ chat log
    def say(self, who, text, kind=""):
        with self.lock:
            self.s["chat"].append(dict(t=time.strftime("%H:%M:%S"), who=who, text=text, kind=kind))
            del self.s["chat"][:-200]

    # ------------------------------------------------------------------ manual drive
    def drive(self, v, w):
        """Hold-to-drive from the page: keep publishing while requests keep coming (dead-man 0.4 s)."""
        if not self.teleop_active:
            self.cancel_all("수동 조작")
        self.teleop = (max(-0.3, min(0.3, v)), max(-0.8, min(0.8, w)), time.time())

    def teleop_tick(self):
        v, w, t = self.teleop
        if time.time() - t < 0.4:
            self.teleop_active = True
            msg = Twist()
            msg.linear.x, msg.angular.z = float(v), float(w)
            self.cmd_vel.publish(msg)
        elif self.teleop_active:                       # released: one zero command, then stay quiet (Nav2 owns /cmd_vel)
            self.teleop_active = False
            self.cmd_vel.publish(Twist())

    # ------------------------------------------------------------------ Nav2
    def go_to(self, x, y, yaw, label=""):
        if self.s["busy"]:
            raise RuntimeError("미션 실행 중에는 이동 명령을 보낼 수 없습니다 (먼저 중지)")
        if not self.nav.wait_for_server(timeout_sec=2.0):
            raise RuntimeError("Nav2 가 준비되지 않았습니다")
        self.cancel_nav()
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = float(x), float(y)
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        name = label or f"({x:.2f}, {y:.2f})"
        with self.lock:
            self.s["nav"] = dict(state="이동 중", goal=[round(x, 2), round(y, 2), round(yaw, 2)], remaining=None, label=name)

        def on_fb(m):
            with self.lock:
                self.s["nav"]["remaining"] = round(m.feedback.distance_remaining, 2)

        def on_accept(future):
            handle = future.result()
            if not handle.accepted:
                with self.lock:
                    self.s["nav"]["state"] = "거부됨"
                return
            self.nav_handle = handle
            handle.get_result_async().add_done_callback(on_done)

        def on_done(future):
            status = future.result().status
            self.nav_handle = None                     # finished: nothing left to cancel
            with self.lock:
                self.s["nav"]["state"] = NAV_STATUS.get(status, f"상태 {status}")
            self.say("시스템", f"{name}: {NAV_STATUS.get(status, status)}", "nav")

        self.nav.send_goal_async(goal, feedback_callback=on_fb).add_done_callback(on_accept)
        self.say("시스템", f"{name} 으로 이동 시작", "nav")

    def cancel_nav(self):
        if self.nav_handle is not None:
            self.nav_handle.cancel_goal_async()
            self.nav_handle = None

    def cancel_all(self, why=""):
        if self.nav_handle is not None:
            self.cancel_nav()
            with self.lock:
                self.s["nav"]["state"] = "취소됨"
        if self.plan_handle is not None:
            self.plan_handle.cancel_goal_async()
            if why:
                self.say("시스템", f"미션 중지 ({why})", "mission")

    # ------------------------------------------------------------------ LLM missions
    def execute_plan(self, plan, text):
        """Executor for PlanDialogManager: send the plan to the Task Manager and wait (in the chat worker thread)."""
        if not self.plan_client.wait_for_server(timeout_sec=3.0):
            raise RuntimeError("Task Manager(/execute_plan)가 없습니다. ./scripts/robotworld start 로 띄웠는지 확인하세요")
        self.cancel_nav()
        steps = [s.note or s.describe() for s in plan.steps]
        with self.lock:
            self.s["mission"] = dict(active=True, step=0, total=len(steps), action="", detail="", steps=steps)
            self.s["pending"] = False                  # confirmed: hide the 진행/취소 buttons while it runs
        done = threading.Event()
        box = {}

        def on_fb(m):
            f = m.feedback
            with self.lock:
                self.s["mission"].update(step=int(f.step), total=int(f.total), action=f.action, detail=f"{f.phase}: {f.detail}")
            if f.phase == "start":
                self.say("로봇", f"[{f.step + 1}/{f.total}] {f.detail}", "step")

        def on_accept(future):
            handle = future.result()
            if not handle.accepted:
                box["result"] = None
                done.set()
                return
            self.plan_handle = handle
            handle.get_result_async().add_done_callback(lambda r: (box.update(result=r.result().result), done.set()))

        self.plan_client.send_goal_async(plan.to_msg(text), feedback_callback=on_fb).add_done_callback(on_accept)
        done.wait()
        self.plan_handle = None
        with self.lock:
            self.s["mission"]["active"] = False
        result = box.get("result")
        if result is None:
            raise RuntimeError("Task Manager 가 계획을 받지 않았습니다 (다른 작업 중)")
        return result

    def chat(self, text):
        """One user sentence through the dialog manager (runs in a worker thread; replies go to the chat log)."""
        self.say("사용자", text, "user")
        if not self.chat_lock.acquire(blocking=False):
            self.say("시스템", "앞 문장을 처리 중입니다. 끝난 뒤에 다시 말씀해 주세요.", "warn")
            return
        try:
            with self.lock:
                self.s["busy"] = True
            if self.dialog is None:
                # speak() is called for every reply at the moment it is made (ask back, confirm, "will do", result)
                self.dialog = PlanDialogManager(PlanParser(), executor=self.execute_plan,
                                                speak=lambda t: self.say("로봇", t, "reply"), world=self.world_state)
            self.dialog.handle(text)
        except Exception as error:                     # LLM / network / ROS: tell the user instead of dying
            self.say("시스템", f"오류: {error}", "error")
        finally:
            with self.lock:
                self.s["busy"] = False
                self.s["pending"] = bool(self.dialog and self.dialog.pending is not None)
            self.chat_lock.release()

    # ------------------------------------------------------------------ camera
    def set_camera(self, on):
        FRAMES.mkdir(parents=True, exist_ok=True)
        flag = FRAMES / "enabled"
        if on:
            flag.touch()
        else:
            flag.unlink(missing_ok=True)
            for f in FRAMES.glob("*.jpg"):
                f.unlink(missing_ok=True)
        self.put(camera=bool(on))

    # ------------------------------------------------------------------ snapshot
    def places(self):
        out = []
        for key, loc in self.locations.locations.items():
            out.append(dict(key=key, label=PLACE_KO.get(key, (loc.get("aliases") or [key])[0]), center=loc["center"],
                            goal=loc["base_goal"], station=bool(loc.get("station"))))
        return out

    def snapshot(self):
        with self.lock:
            s = json.loads(json.dumps(self.s))
        s["sim_time"] = round(self.get_clock().now().nanoseconds * 1e-9, 1)
        s["map_version"] = self.map_meta and self.map_meta["version"]
        s["world"] = self.world_state.describe()
        return s


def make_app(fms):
    app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")

    def ok(**kw):
        return jsonify(ok=True, **kw)

    def fail(error, code=400):
        return jsonify(ok=False, error=str(error)), code

    @app.get("/")
    def index():
        return send_from_directory(HERE / "static", "index.html")

    @app.get("/api/stream")
    def stream():
        def gen():
            while True:
                yield f"data: {json.dumps(fms.snapshot(), ensure_ascii=False)}\n\n"
                time.sleep(0.2)
        return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/api/static_info")
    def static_info():
        return jsonify(places=fms.places(), cups={n: TARGET_KO.get(n, n) for n in fms.cup_names},
                       cup_colors={o["name"]: o["rgba"][:3] for o in fms.world["objects"]})

    @app.get("/api/map")
    def map_meta():
        return jsonify(fms.map_meta or {})

    @app.get("/api/map.png")
    def map_png():
        if fms.map_png is None:
            return "no /map yet", 404
        return Response(fms.map_png, mimetype="image/png", headers={"Cache-Control": "no-cache"})

    @app.post("/api/drive")
    def drive():
        d = request.get_json(silent=True) or {}
        fms.drive(float(d.get("v", 0.0)), float(d.get("w", 0.0)))
        return ok()

    @app.post("/api/goal")
    def goal():
        d = request.get_json(silent=True) or {}
        try:
            if "place" in d:
                key = fms.locations.resolve(d["place"])
                if key is None:
                    return fail(f"모르는 장소: {d['place']}")
                x, y, yaw = fms.locations.goal(key)
                fms.go_to(x, y, yaw, PLACE_KO.get(key, key))
            else:
                fms.go_to(float(d["x"]), float(d["y"]), float(d.get("yaw", 0.0)))
        except (KeyError, ValueError) as error:
            return fail(f"x, y, yaw 또는 place 가 필요합니다 ({error})")
        except RuntimeError as error:
            return fail(error, 409)
        return ok()

    @app.post("/api/stop")
    def stop():
        fms.cancel_all("정지 버튼")
        fms.teleop = (0.0, 0.0, 0.0)
        fms.cmd_vel.publish(Twist())
        return ok()

    @app.post("/api/chat")
    def chat():
        text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
        if not text:
            return fail("빈 문장")
        threading.Thread(target=fms.chat, args=(text,), daemon=True).start()
        return ok()

    @app.post("/api/camera")
    def camera():
        fms.set_camera(bool((request.get_json(silent=True) or {}).get("on")))
        return ok(camera=fms.s["camera"])

    @app.get("/api/cameras")
    def cameras():
        meta = FRAMES / "meta.json"
        return jsonify(json.loads(meta.read_text()) if meta.exists() else {})

    @app.get("/camera/<name>.mjpg")
    def camera_stream(name):
        path = FRAMES / f"{Path(name).name}.jpg"

        def gen():
            last = None
            while fms.s["camera"]:
                try:
                    mtime = path.stat().st_mtime_ns
                    if mtime != last:
                        last = mtime
                        jpg = path.read_bytes()
                        yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n"
                except FileNotFoundError:
                    pass
                time.sleep(0.05)
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open it to other PCs on the network")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)     # Ctrl+C goes to Flask
    fms = Fms()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(fms)
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    print(f"FMS: http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{a.port}", flush=True)
    try:
        make_app(fms).run(host=a.host, port=a.port, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        fms.set_camera(False)
        executor.shutdown()
        spinner.join(timeout=2)
        fms.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
