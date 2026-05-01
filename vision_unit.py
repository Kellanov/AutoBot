"""vision_worker — captures frames from the camera and emits detections."""
import platform
import signal
import sys

import cv2

from vision import VisionSystem


# Module-level flag flipped by signal handlers so the loop can exit cleanly
_shutdown_requested = False

def _request_shutdown(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True


def _open_camera():
    """IMX219 CSI camera on Jetson via GStreamer, or webcam on Mac."""
    if platform.system() == "Darwin":
        return cv2.VideoCapture(0)

    pipeline = (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), width=640, height=480, framerate=30/1 ! "
        "nvvidconv ! video/x-raw, format=BGRx ! "
        "videoconvert ! video/x-raw, format=BGR ! "
        "appsink drop=1"
    )
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if cap.isOpened():
        print("--- JETSON MODE: IMX219 CSI camera opened via GStreamer ---")
        return cap
    print("--- JETSON WARNING: GStreamer failed, falling back to /dev/video0 ---")
    return cv2.VideoCapture(0)


def vision_worker(vision_queue):
    # Catch SIGTERM (from the parent's terminate()) and SIGINT (Ctrl+C) so
    # we get a chance to release the camera before exiting. On Jetson, an
    # unclean exit leaves the Argus daemon holding the camera lock.
    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)

    on_mac = platform.system() == "Darwin"
    vision = VisionSystem()
    cap = _open_camera()

    # On Jetson, the GStreamer pipeline already has width/height baked in.
    # Calling cap.set() on a GStreamer pipeline triggers a teardown/rebuild
    # that Argus can't recover from. Only set properties on the Mac webcam.
    if on_mac:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    img_center = frame_width / 2

    FOCAL_REF = 550
    KNOWN_HEIGHTS = {
        "person": 1.7, "bottle": 0.25, "chair": 0.8,
        "cell phone": 0.15, "laptop": 0.25,
    }

    while not _shutdown_requested:
        if not cap.grab():
            break
        ok, frame = cap.retrieve()
        if not ok:
            continue

        detections_to_send = []
        for det in vision.detect(frame):
            x1, y1, x2, y2 = det["xyxy"]
            x_center, _, _, h_px = det["xywh"]

            offset = (x_center - img_center) / img_center
            label = det["label"]
            conf = det["conf"]

            real_h = KNOWN_HEIGHTS.get(label, 0.5)
            dist_est = (real_h * FOCAL_REF) / h_px if h_px > 0 else 0.0

            if on_mac:
                color = (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                text = f"{label} {conf:.2f} | {dist_est:.1f}m"
                cv2.putText(frame, text, (x1, max(y1 - 10, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                cv2.line(frame, (int(img_center), 0),
                         (int(img_center), frame_height), (255, 0, 0), 1)

            detections_to_send.append({
                "label": label,
                "conf": conf,
                "offset": offset,
                "visual_dist": dist_est,
            })

        if on_mac:
            cv2.imshow("Bot Vision Debug", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        # Only send if the consumer is ready (drops stale detections)
        if vision_queue.empty():
            vision_queue.put(detections_to_send)

    print("--- Vision worker releasing camera... ---", file=sys.stderr)
    cap.release()
    if on_mac:
        cv2.destroyAllWindows()
    print("--- Vision worker stopped. ---", file=sys.stderr)
