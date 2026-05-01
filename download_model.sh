#!/usr/bin/env bash
# Download YOLOv3-tiny model files for OpenCV DNN.
# YOLOv3-tiny is supported by OpenCV >= 3.4 (so works on Jetson's 4.1.1).
# YOLOv4-tiny needs OpenCV >= 4.4 — DON'T use it on JetPack 4.x.
#
# Run once: ./download_model.sh
set -e

cd "$(dirname "$0")"
mkdir -p model
cd model

echo "[1/3] yolov3-tiny.cfg..."
[ -f yolov3-tiny.cfg ] || wget -L --show-progress \
  https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3-tiny.cfg

echo "[2/3] yolov3-tiny.weights (~34 MB)..."
[ -f yolov3-tiny.weights ] || wget -L --show-progress \
  https://pjreddie.com/media/files/yolov3-tiny.weights

echo "[3/3] coco.names..."
[ -f coco.names ] || wget -L --show-progress \
  https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names

echo ""
echo "Done. Files in $(pwd):"
ls -lh

echo ""
echo "Sanity check (should say 'data', NOT 'HTML' or 'ASCII'):"
file yolov3-tiny.weights
