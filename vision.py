"""VisionSystem — object detection via OpenCV's DNN module.

No PyTorch / torchvision / ultralytics / yolov5 required. Loads YOLOv4-tiny
in Darknet format, which OpenCV 4.x can parse natively.

Model files are fetched by vision_only/download_model.sh:
    yolov4-tiny.cfg, yolov4-tiny.weights, coco.names

Set ROSBOT_VISION_DEBUG=1 in the environment to print raw detection counts
on every frame so you can see if the model is producing anything at all.
"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np


class VisionSystem:
    def __init__(self, conf_threshold=0.25, nms_threshold=0.4, input_size=320):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size
        self.debug = os.environ.get("ROSBOT_VISION_DEBUG", "0") == "1"

        cfg, weights, names = self._find_model_files()

        weight_size_mb = weights.stat().st_size / (1024 * 1024)
        print(f"--- Loading {weights.stem} ({weight_size_mb:.1f} MB) "
              f"from {cfg.parent} ---")
        if weight_size_mb < 8:
            print("    WARNING: weights file looks truncated! "
                  "Re-run vision_only/download_model.sh", file=sys.stderr)
        self.net = cv2.dnn.readNetFromDarknet(str(cfg), str(weights))

        # Prefer CUDA; fall back to CPU. Older OpenCV (< 4.2) doesn't even define
        # the CUDA constants, hence the AttributeError catch alongside cv2.error.
        cuda_backend = getattr(cv2.dnn, "DNN_BACKEND_CUDA", None)
        cuda_target = getattr(cv2.dnn, "DNN_TARGET_CUDA", None)
        if cuda_backend is not None and cuda_target is not None:
            try:
                self.net.setPreferableBackend(cuda_backend)
                self.net.setPreferableTarget(cuda_target)
                print("--- DNN backend: CUDA ---")
            except cv2.error:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                print("--- DNN backend: CPU (CUDA setup failed) ---")
        else:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            print("--- DNN backend: CPU (OpenCV built without CUDA DNN) ---")

        layer_names = self.net.getLayerNames()
        unconnected = self.net.getUnconnectedOutLayers()
        if unconnected.ndim == 2:
            unconnected = unconnected.flatten()
        self.output_layers = [layer_names[i - 1] for i in unconnected]

        with open(names) as f:
            self.class_names = [line.strip() for line in f if line.strip()]

    @staticmethod
    def _find_model_files():
        """Look for YOLO model files. Prefers v3-tiny (works on OpenCV 4.1+),
        falls back to v4-tiny (only works on OpenCV >= 4.4).
        """
        here = Path(__file__).resolve().parent
        dirs = [here / "model", here / "vision_only" / "model"]
        # (cfg_name, weights_name) pairs in priority order
        model_variants = [
            ("yolov3-tiny.cfg", "yolov3-tiny.weights"),
            ("yolov4-tiny.cfg", "yolov4-tiny.weights"),
        ]
        for d in dirs:
            for cfg_name, w_name in model_variants:
                cfg = d / cfg_name
                weights = d / w_name
                names = d / "coco.names"
                if cfg.exists() and weights.exists() and names.exists():
                    return cfg, weights, names

        sys.stderr.write(
            "ERROR: No YOLO model files found.\n"
            "Run: cd vision_only && ./download_model.sh\n"
        )
        sys.exit(1)

    def detect(self, frame):
        """Yield {'label', 'conf', 'xyxy', 'xywh'} dicts for each detection."""
        h, w = frame.shape[:2]

        blob = cv2.dnn.blobFromImage(
            frame, 1 / 255.0, (self.input_size, self.input_size),
            swapRB=True, crop=False,
        )
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        boxes, confidences, class_ids = [], [], []
        max_raw_conf = 0.0
        max_raw_label = ""
        for out in outs:
            for det in out:
                scores = det[5:]
                class_id = int(np.argmax(scores))
                confidence = float(scores[class_id])
                if confidence > max_raw_conf:
                    max_raw_conf = confidence
                    max_raw_label = self.class_names[class_id]
                if confidence < self.conf_threshold:
                    continue
                cx, cy, bw, bh = det[0:4] * np.array([w, h, w, h])
                x1 = int(cx - bw / 2)
                y1 = int(cy - bh / 2)
                boxes.append([x1, y1, int(bw), int(bh)])
                confidences.append(confidence)
                class_ids.append(class_id)

        if self.debug:
            print(f"[vision] raw boxes above threshold: {len(boxes)} | "
                  f"max raw conf: {max_raw_conf:.3f} ({max_raw_label})")

        idxs = cv2.dnn.NMSBoxes(boxes, confidences,
                                self.conf_threshold, self.nms_threshold)
        if len(idxs) == 0:
            return
        if hasattr(idxs, "flatten"):
            idxs = idxs.flatten()

        for i in idxs:
            x, y, bw, bh = boxes[i]
            yield {
                "label": self.class_names[class_ids[i]],
                "conf":  confidences[i],
                "xyxy":  (x, y, x + bw, y + bh),
                "xywh":  (x + bw / 2.0, y + bh / 2.0, float(bw), float(bh)),
            }
