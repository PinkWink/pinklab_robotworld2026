"""Save slam_toolbox's pose graph markers (/slam_toolbox/graph_visualization) to a pickle for draw_lesson04_figures.py.

    ./scripts/robotworld exec python3 docs/camp/slam_graph_capture.py artifacts/dev/slam_graph.pkl
Each marker becomes (ns, id, type, [(x, y) of its points], (pose x, pose y)).
"""
import pickle
import sys

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import MarkerArray

rclpy.init()
n = Node("slam_graph_capture")
got = {}
n.create_subscription(MarkerArray, "/slam_toolbox/graph_visualization", lambda m: got.setdefault("m", m), 10)
while "m" not in got:
    rclpy.spin_once(n, timeout_sec=0.5)
rows = [(m.ns, m.id, m.type, [(p.x, p.y) for p in m.points], (m.pose.position.x, m.pose.position.y)) for m in got["m"].markers]
pickle.dump(rows, open(sys.argv[1], "wb"))
print("markers", len(rows), {r[0] for r in rows})
n.destroy_node(); rclpy.shutdown()
