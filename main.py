"""ROSBot — vision + audio only.

Vision runs in a worker process; the main process consumes detections
and announces them via AudioFeedback.
"""
import multiprocessing
import time

from vision_unit import vision_worker
from audio_unit import AudioFeedback

# How long to wait before re-announcing a label that's still in view
REPEAT_AFTER_SEC = 8.0


def main():
    multiprocessing.set_start_method("spawn", force=True)

    v_queue = multiprocessing.Queue(maxsize=1)
    vision_proc = multiprocessing.Process(target=vision_worker, args=(v_queue,))
    vision_proc.start()

    speaker = AudioFeedback(cooldown=1.5)
    last_announced = {}  # label -> timestamp

    print("--- ROSBot active (vision + audio) — Ctrl+C to stop ---")

    # Confirm the audio path is working by speaking on startup. If you don't
    # hear this line, the audio chain is broken — not the vision pipeline.
    time.sleep(1.0)  # let the worker print its init lines first
    speaker.speak("ROSBot online")

    frames_seen = 0
    detections_seen = 0
    last_heartbeat = time.time()

    try:
        while True:
            # Heartbeat every 5s so you can see the script is alive even with
            # no detections.
            now = time.time()
            if now - last_heartbeat >= 5.0:
                print(f"[heartbeat] frames={frames_seen} "
                      f"detections={detections_seen} "
                      f"({frames_seen / max(now - last_heartbeat, 0.1):.1f} fps)")
                frames_seen = 0
                detections_seen = 0
                last_heartbeat = now

            if v_queue.empty():
                time.sleep(0.05)
                continue

            detections = v_queue.get()
            frames_seen += 1
            if not detections:
                continue
            detections_seen += len(detections)

            # Pick the highest-confidence detection per label this frame
            top_per_label = {}
            for d in detections:
                if d["conf"] > top_per_label.get(d["label"], 0):
                    top_per_label[d["label"]] = d["conf"]

            now = time.time()
            for label, conf in top_per_label.items():
                last = last_announced.get(label, 0)
                if now - last >= REPEAT_AFTER_SEC:
                    print(f"[see] {label} ({conf:.2f})")
                    speaker.speak(f"I see a {label}")
                    last_announced[label] = now
    except KeyboardInterrupt:
        print("\n--- Shutting down ---")
    finally:
        # Graceful shutdown: SIGTERM first so vision_worker can release the
        # camera. Only escalate to SIGKILL if it doesn't exit in time.
        if vision_proc.is_alive():
            vision_proc.terminate()         # sends SIGTERM
            vision_proc.join(timeout=5)     # wait for clean release
        if vision_proc.is_alive():
            print("--- Vision worker didn't exit, killing... ---")
            vision_proc.kill()              # SIGKILL
            vision_proc.join(timeout=2)


if __name__ == "__main__":
    main()
