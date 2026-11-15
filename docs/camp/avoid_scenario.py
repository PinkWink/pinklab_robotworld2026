"""A visitor who is not on the map stands in the robot's way while Nav2 drives it through the booth.

    ./scripts/robotworld nav moveit:=false actors:=$PWD/src/mobile_openarm_mujoco/worlds/actors_avoid.yaml   # 터미널 1
    ./scripts/robotworld exec python3 docs/camp/avoid_scenario.py                    # 터미널 2: standing (기본)
    ./scripts/robotworld exec python3 docs/camp/avoid_scenario.py --mode blocked     # 길을 완전히 막은 경우
    ./scripts/robotworld exec python3 docs/camp/avoid_scenario.py --mode clear       # 사람이 비켜난 뒤 다시

standing: the visitor stands at (6.30, -3.50), a little south of the straight line home -> info; goal = info (7.43, -3.77, -1.15)
blocked:  the visitor stands at (5.35, -4.50), the middle of the only passage to the entrance; goal = entrance (5.98, -5.53, -1.55)
clear:    the visitor goes back outside the booth; goal = entrance again
Uses /warehouse/set_actor (teleport), then NavigateToPose, and prints the closest robot-visitor distance.
"""
import argparse
import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from warehouse_interfaces.msg import ActorStateArray
from warehouse_interfaces.srv import SetActor

VISITOR = "visitor_standing"
OUTSIDE = (10.5, -7.5)
SCENES = {"standing": ((6.30, -3.50), (7.43, -3.77, -1.15)),
          "blocked": ((5.35, -4.50), (5.98, -5.53, -1.55)),
          "clear": (OUTSIDE, (5.98, -5.53, -1.55))}


class Scenario(Node):
    def __init__(self):
        super().__init__("avoid_scenario", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.actor = self.create_client(SetActor, "/warehouse/set_actor")
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.robot = self.visitor = None
        self.closest = (float("inf"), 0.0)
        self.create_subscription(PoseStamped, "/ground_truth", self.on_truth, 10)
        self.create_subscription(ActorStateArray, "/warehouse/actor_states", self.on_actors, 10)

    def on_truth(self, m):
        self.robot = (m.pose.position.x, m.pose.position.y)
        if self.visitor:
            d = math.dist(self.robot, self.visitor)
            if d < self.closest[0]:
                self.closest = (d, self.get_clock().now().nanoseconds * 1e-9)

    def on_actors(self, m):
        for a in m.actors:
            if a.name == VISITOR:
                self.visitor = (a.pose.position.x, a.pose.position.y)

    def place(self, x, y):
        pose = PoseStamped().pose
        pose.position.x, pose.position.y = x, y
        future = self.actor.call_async(SetActor.Request(name=VISITOR, operation="teleport", pose=pose))
        rclpy.spin_until_future_complete(self, future, timeout_sec=5)
        print(f"set_actor teleport ({x:.2f}, {y:.2f}): {future.result().success} {future.result().message}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=list(SCENES), default="standing")
    ap.add_argument("--timeout", type=float, default=120.0, help="give up (cancel the goal) after this many seconds of wall time")
    a = ap.parse_args()
    rclpy.init()
    n = Scenario()
    n.actor.wait_for_service(timeout_sec=10)
    n.nav.wait_for_server(timeout_sec=30)
    (px, py), (gx, gy, gyaw) = SCENES[a.mode]
    n.place(px, py)
    end = time.monotonic() + 2.0                        # let the lidar see the visitor before planning
    while time.monotonic() < end:
        rclpy.spin_once(n, timeout_sec=0.05)
    goal = NavigateToPose.Goal()
    goal.pose.header.frame_id = "map"
    goal.pose.pose.position.x, goal.pose.pose.position.y = gx, gy
    goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(gyaw / 2), math.cos(gyaw / 2)
    start = time.monotonic()
    handle = n.nav.send_goal_async(goal)
    rclpy.spin_until_future_complete(n, handle, timeout_sec=10)
    print(f"goal ({gx}, {gy}, {gyaw}) accepted: {handle.result().accepted}", flush=True)
    result = handle.result().get_result_async()
    while not result.done():
        rclpy.spin_once(n, timeout_sec=0.05)
        if time.monotonic() - start > a.timeout:
            print(f"no result after {a.timeout:.0f} s: cancelling the goal", flush=True)
            rclpy.spin_until_future_complete(n, handle.result().cancel_goal_async(), timeout_sec=5)
            a.timeout = float("inf")
    status = result.result().status
    names = {GoalStatus.STATUS_SUCCEEDED: "SUCCEEDED", GoalStatus.STATUS_ABORTED: "ABORTED", GoalStatus.STATUS_CANCELED: "CANCELED"}
    print(f"NavigateToPose result: {names.get(status, status)}  {time.monotonic() - start:.1f} s", flush=True)
    if n.closest[0] < 5:
        print(f"closest robot-visitor distance: {n.closest[0]:.2f} m (centre to centre)", flush=True)
    n.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
