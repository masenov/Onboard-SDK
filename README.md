**To build Onboard-SDK**

cd build

cmake ..

make

**To run Onboard-SDK**

Executables are located inside the build/bin folder

**To install OSDK**

cd build

cmake ..

make djiosdk-core

sudo make install djiosdk-core


**To build Onboard-SDK-ROS**

cd catkin_ws/src

catkin_make

source devel/setup.bash

(to setup for first time) rosed dji_sdk sdk.launch


**To run Onboard-SDK-ROS**

roslaunch dji_sdk sdk.launch

And in another terminal...

rosrun dji_sdk_demo demo_flight_control
