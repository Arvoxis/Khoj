"""
KHOJ — Jetson live detection stream (headless-friendly visual).

Runs the TensorRT engine on the ArduCam and serves the ANNOTATED video (boxes +
confidences) as an MJPEG stream over HTTP. Because the Jetson is usually headless
(SSH over USB-C), you watch it in a browser on your laptop instead of a local
window — great for a demo/projector.

    # USB (UVC) ArduCam:
    python3 jetson_stream.py --engine ~/best.engine --source 0
    # CSI (MIPI) ArduCam:
    python3 jetson_stream.py --engine ~/best.engine --csi

Then on your LAPTOP open:   http://192.168.55.1:8090
(that's the Jetson's USB-gadget IP; use its Ethernet/Wi-Fi IP if you prefer.)

Notes:
  * USB ArduCam works with any OpenCV. CSI needs GStreamer-enabled OpenCV
    (JetPack's system OpenCV has it; some pip opencv-python wheels do not).
  * Hold the camera close enough that a person fills a good part of the frame —
    aerial people are small, so a distant phone screen is the usual failure mode.
"""

from __future__ import annotations

import argparse
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

_latest = {"jpg": None, "n": 0, "ms": 0.0, "fps": 0.0}
_lock = threading.Lock()
_stop = threading.Event()


def csi_pipeline(w=1280, h=720, fps=30, sensor_id=0):
    return (f"nvarguscamerasrc sensor-id={sensor_id} ! "
            f"video/x-raw(memory:NVMM),width={w},height={h},framerate={fps}/1 ! "
            f"nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! "
            f"video/x-raw,format=BGR ! appsink drop=true max-buffers=1")


def open_camera(args):
    if args.csi:
        cap = cv2.VideoCapture(csi_pipeline(args.width, args.height, args.fps,
                                            args.sensor_id), cv2.CAP_GSTREAMER)
    else:
        src = int(args.source) if str(args.source).isdigit() else args.source
        cap = cv2.VideoCapture(src)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    return cap


def infer_loop(args):
    from ultralytics import YOLO
    model = YOLO(args.engine)
    cap = open_camera(args)
    if not cap or not cap.isOpened():
        print("ERROR: could not open camera. USB: try --source 1/2. "
              "CSI: use --csi (needs GStreamer OpenCV).")
        _stop.set(); return
    print("camera open — inference running. Point a browser at "
          f"http://<jetson-ip>:{args.port}\n")
    t_prev = time.time()
    while not _stop.is_set():
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.02); continue
        r = model(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)[0]
        ann = r.plot()
        now = time.time(); fps = 1.0 / max(now - t_prev, 1e-6); t_prev = now
        n = len(r.boxes); ms = r.speed.get("inference", 0.0)
        # header banner
        cv2.rectangle(ann, (0, 0), (ann.shape[1], 34), (40, 25, 15), -1)
        cv2.putText(ann, f"KHOJ  |  persons: {n}   {ms:.1f} ms   {fps:.0f} FPS",
                    (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        ok2, buf = cv2.imencode(".jpg", ann, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ok2:
            with _lock:
                _latest.update(jpg=buf.tobytes(), n=n, ms=ms, fps=fps)
    cap.release()


class Handler(BaseHTTPRequestHandler):
    def _page(self):
        html = (b"<html><head><title>KHOJ live</title></head>"
                b"<body style='margin:0;background:#0d0f14;text-align:center'>"
                b"<img src='/stream' style='max-width:100vw;max-height:100vh'></body></html>")
        self.send_response(200); self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(html))); self.end_headers()
        self.wfile.write(html)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._page()
        if self.path != "/stream":
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while not _stop.is_set():
                with _lock:
                    jpg = _latest["jpg"]
                if jpg:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                     b"Content-Length: " + str(len(jpg)).encode() +
                                     b"\r\n\r\n" + jpg + b"\r\n")
                time.sleep(0.04)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="best.engine")
    ap.add_argument("--source", default="0", help="USB camera index (or file/rtsp)")
    ap.add_argument("--csi", action="store_true", help="use CSI camera via nvarguscamerasrc")
    ap.add_argument("--sensor-id", type=int, default=0)
    ap.add_argument("--conf", type=float, default=0.30)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--port", type=int, default=8090)
    args = ap.parse_args()

    th = threading.Thread(target=infer_loop, args=(args,), daemon=True)
    th.start()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"serving live stream on port {args.port}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _stop.set(); srv.shutdown()


if __name__ == "__main__":
    main()
