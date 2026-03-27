from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'opentcs_ros2_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@example.com',
    description='Bridge: OpenTCS vehicle adapter (TCP) <-> ROS2 Nav2',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'bridge_node = opentcs_ros2_bridge.bridge_node:main',
            'logic_sim_robot = opentcs_ros2_bridge.logic_sim_robot:main',
            'opentcs_map_coord = opentcs_ros2_bridge.coordinate_mapping:main_cli',
        ],
    },
)
