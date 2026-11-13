from pathlib import Path
from setuptools import setup

name = "robotworld"
data = [("share/ament_index/resource_index/packages", ["resource/" + name]), ("share/" + name, ["package.xml"])]
files = [p for p in Path("booth").rglob("*") if p.is_file()]
for directory in sorted({p.parent for p in files}):
    data.append(("share/" + name + "/" + str(directory), [str(p) for p in sorted(files) if p.parent == directory]))
setup(name=name, version="0.1.0", packages=[name], data_files=data, install_requires=["setuptools"], zip_safe=False)
