"""Record a run so it can be re-rendered offline at any frame rate and camera angle (intro video).

    ./scripts/robotworld exec python video/record.py artifacts/video/run.pkl      # until Ctrl+C / SIGTERM
Sim-time stamps: states (/joint_states), base (/ground_truth), objects (/warehouse/object_poses),
plan_fb (/execute_plan feedback), sync = (sim time, wall time) every 0.2 s wall (to line up browser frames).
"""
import pickle
import signal
import sys
import time

import rclpy
from geometry_msgs.msg import PoseArray, PoseStamped
from rclpy.node import Node
from rclpy.parameter import Parameter
from sensor_msgs.msg import JointState
from warehouse_interfaces.action import ExecutePlan


def stamp(s):
    return s.sec + s.nanosec * 1e-9


def pose(p):
    return (p.position.x, p.position.y, p.position.z, p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w)


def main(out):
    rclpy.init()
    node = Node("video_record", parameter_overrides=[Parameter("use_sim_time", value=True)])
    now = lambda: node.get_clock().now().nanoseconds * 1e-9  # noqa: E731
    data = dict(states=[], base=[], objects=[], plan_fb=[], sync=[])
    node.create_subscription(JointState, "/joint_states",
                             lambda m: data["states"].append(dict(t=stamp(m.header.stamp), names=list(m.name), positions=list(m.position))), 100)
    node.create_subscription(PoseStamped, "/ground_truth", lambda m: data["base"].append(dict(t=stamp(m.header.stamp), pose=pose(m.pose))), 50)
    node.create_subscription(PoseArray, "/warehouse/object_poses", lambda m: data["objects"].append(dict(t=now(), poses=[pose(p) for p in m.poses])), 20)
    node.create_subscription(ExecutePlan.Impl.FeedbackMessage, "/execute_plan/_action/feedback",
                             lambda m: data["plan_fb"].append(dict(t=now(), step=m.feedback.step, total=m.feedback.total, action=m.feedback.action,
                                                                   phase=m.feedback.phase, detail=m.feedback.detail)), 50)
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    signal.signal(signal.SIGINT, lambda *_: stop.append(1))
    last = 0.0
    while not stop:
        rclpy.spin_once(node, timeout_sec=0.05)
        if time.time() - last > 0.2:
            last = time.time()
            data["sync"].append((now(), last))
    with open(out, "wb") as f:
        pickle.dump(data, f)
    print("wrote", out, {k: len(v) for k, v in data.items()}, flush=True)
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main(sys.argv[1])
