# Autonomous Vehicle / Bot

**ECE 428 — Embedded Computer Systems | Final Project**
**Author:** Keller Wilson
**Advisor:** Dr. Anthony Choi, Mercer University, Department of Electrical and Computer Engineering
**Acknowledgement:** This project was supported in part by NASA. Thanks to NASA for their continued support of student research at Mercer University.

---

## Project Overview

This project is a small-scale autonomous ground vehicle that emulates the core functions of a full-size self-driving car. It uses onboard sensing (LiDAR and camera) to drive itself from a starting point to a destination while detecting and avoiding obstacles along the way. Navigation is handled entirely from onboard sensors — ranging from LiDAR and visual context from the camera — fused on an NVIDIA Jetson Nano running ROS, mounted on the Waveshare JetBot ROS AI Kit chassis.

The project deliverable is a working bot that can:

- Reach a target destination with high accuracy
- Identify obstacles and objects in its path
- Avoid those obstacles while continuing toward the destination
- Operate in a variety of environments, both indoors and outdoors

---

## Problem Statement

Verifying the safety and efficacy of full-size self-driving cars is expensive, time-consuming, and largely impractical for a single researcher or student. Companies developing autonomous vehicles rely on large simulation fleets and dedicated test tracks that are out of reach for academic embedded-systems work. A small-scale bot that emulates the same sensor stack and decision logic is a low-cost, low-risk way to study the behavior of autonomous navigation algorithms in real environments.

This project takes that approach: rather than simulating an AV, it builds one at small scale using the same categories of sensors (ranging, vision) and actuators (drive motors, audio output) found on a full vehicle.

---

## System Architecture

```
                    +---------------------+
   RPLiDAR A1 ----->|                     |-----> Motor Controls
                    |    Jetson Nano      |
   Pi Camera  ----->|       (ROS)         |-----> 8Ω 2W Speaker
                    +---------------------+
```

**Inputs (Sensors):**
- **RPLiDAR A1** — 360° 2D laser scanner, used for obstacle detection and local mapping
- **Raspberry Pi Camera** — used for object/obstacle classification and visual cues

**Outputs (Actuators):**
- **Dual DC motor drive** — controls left/right wheel speed for differential steering
- **8Ω 2W speaker** — audio feedback (alerts, status, obstacle warnings)

The Jetson Nano runs all sensor drivers and the navigation logic, fusing LiDAR ranges and camera classifications to produce motor commands in real time.

---

## Hardware

| Component | Purpose | Approx. Cost |
|---|---|---|
| Waveshare JetBot ROS AI Kit (incl. Jetson Nano, chassis, motors, Pi Camera) | Compute + drivetrain + camera | ~$300.00 |
| RPLiDAR A1 | 2D 360° ranging | (included / on-hand) |
| 8Ω 2W speaker | Audio output | ~$1 – $6 |
| Power: 18650 Li-ion cells (kit-supplied) | Onboard power | (included) |
| Jumper wires, mounts, hardware | Integration | minor |

**Total:** approximately $305 – $315

---

## Software & Libraries

- **OS:** NVIDIA JetPack (Ubuntu-based) on Jetson Nano
- **Middleware:** ROS (Robot Operating System) — the JetBot ROS AI Kit ships with a ROS workspace
- **Languages:** Python 3 (high-level navigation and node logic), C/C++ (low-level driver code where needed)
- **Key ROS packages / libraries:**
  - `rplidar_ros` — driver and topics for the RPLiDAR A1
  - `jetbot_ros` / Waveshare-provided motor driver nodes — wheel control over I²C
  - `cv_bridge` + OpenCV — image handling for the Pi Camera
  - Custom navigation node that consumes LiDAR scans and camera classifications, and publishes velocity commands

---

## Wiring & Circuits

High-level interconnect:

- **Jetson Nano (carrier board)** is the central controller and is powered from the kit battery pack through the kit's power regulator.
- **RPLiDAR A1** connects to the Jetson via USB. It receives 5 V from the USB line.
- **Pi Camera** connects to the Jetson Nano camera CSI ribbon connector.
- **Motor driver board** (part of the JetBot kit) communicates with the Jetson over **I²C** and switches power to the two DC drive motors. The motors are powered directly from the battery pack, not from the Jetson's regulated rails.
- **Speaker** is driven by a small audio amplifier circuit fed from a PWM/audio output pin on the Jetson; the amplifier is powered from 5 V.

Common-ground all peripherals to the Jetson ground. Keep motor power on its own pair of conductors back to the battery pack to avoid coupling motor noise into the I²C lines.

---

## Code Structure

The high-level control loop is organized as a small set of ROS nodes that publish/subscribe through the ROS graph rather than calling each other directly.

```
sensor nodes  ->  navigation node  ->  actuator nodes
  (lidar,           (fuses inputs,         (motor driver,
   camera)           plans next move)       speaker)
```

The navigation node runs a simple **Sense → Decide → Act** loop:

1. **Sense** — read the latest LiDAR scan and camera frame from the sensor topics.
2. **Decide** — fuse the scan and image to detect obstacles. If an obstacle blocks the path, plan an avoidance maneuver and queue an audio alert; otherwise, hold course toward the target bearing.
3. **Act** — publish a motor command on the velocity topic, which the motor driver node consumes to update wheel speeds.

Position is estimated from commanded velocity and LiDAR features observed in the environment.

---

## Build & Setup Instructions

1. **Flash the Jetson Nano** with the JetPack image included with the Waveshare JetBot ROS AI Kit and complete the kit's first-boot setup.
2. **Assemble the JetBot chassis** following the Waveshare assembly guide (motors, wheels, camera, Jetson Nano, battery pack).
3. **Mount the RPLiDAR A1** on the top deck of the chassis with a clear 360° view and connect it via USB.
4. **Wire the speaker** through a small audio amplifier to the Jetson's audio/PWM output and 5 V.
5. **On the Jetson:** clone this repository into the kit's ROS workspace `src` folder, then run `catkin_make` (or `colcon build` depending on ROS distribution) and `source` the resulting setup script.
6. **Launch the system** with the provided ROS launch file, which starts the LiDAR driver, camera, and the navigation node.
7. **Set a destination** (waypoint) and start the run.

---

## Testing

The bot is evaluated by running it against a target waypoint with obstacles placed along the route. The following are measured:

- **Maneuverability** — can the bot move smoothly through the space?
- **Obstacle detection and avoidance** — does it see and route around obstacles reliably?
- **Object identification** — does the camera-based classifier label objects correctly?
- **Destination accuracy** — how close does it get to the target waypoint?

---

## Results

*To be filled in from the final demo session.* Summary of outcomes from demo runs:

- Destination accuracy and time to destination
- Number of obstacle-avoidance events triggered
- False-positive obstacle calls and their causes
- Smoothness of motion through the test course

---

## References & Resources

- Waveshare JetBot ROS AI Kit — product documentation and assembly guide
- Slamtec RPLiDAR A1 datasheet and `rplidar_ros` package documentation
- NVIDIA Jetson Nano Developer Kit documentation
- ROS (Robot Operating System) documentation, [https://www.ros.org](https://www.ros.org)
- OpenCV documentation, [https://docs.opencv.org](https://docs.opencv.org)
- Course materials, ECE 428 — Embedded Computer Systems, Mercer University

---

*This project was completed for ECE 428 (Embedded Computer Systems) at Mercer University. Special thanks to Dr. Anthony Choi for his guidance throughout the semester, and to NASA for their support of student research.*
