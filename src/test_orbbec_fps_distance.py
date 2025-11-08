import cv2
import time
import numpy as np
import pyorbbecsdk as ob
import os
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# --- redirection silencieuse des erreurs SDK ---
@contextmanager
def suppress_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    os.dup2(devnull, 2)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(devnull)
        os.close(old_stderr)

# --- suivi du curseur ---
mouse_x, mouse_y = -1, -1
def on_mouse(event, x, y, flags, param):
    global mouse_x, mouse_y
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y


def main():
    out_dir = Path("captures")
    out_dir.mkdir(exist_ok=True)

    with suppress_stderr():
        pipeline = ob.Pipeline()
        config = ob.Config()

        # Couleur : 1280×720 RGB à 15 fps (stabilité maximale)
        color_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
        color_profile = color_profiles.get_video_stream_profile(1280, 720, ob.OBFormat.RGB, 15)
        config.enable_stream(color_profile)

        # Profondeur : profil par défaut
        depth_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
        depth_profile = depth_profiles.get_default_video_stream_profile()
        config.enable_stream(depth_profile)

        if hasattr(config, "set_frame_aggregate_output_mode"):
            config.set_frame_aggregate_output_mode(ob.OBFrameAggregateOutputMode.FULL_FRAME_REQUIRE)

        pipeline.start(config)

    prev_time = time.time()
    frame_count = 0
    fps = 0.0

    cv2.namedWindow("RGB | Depth + FPS + Distance")
    cv2.setMouseCallback("RGB | Depth + FPS + Distance", on_mouse)

    try:
        while True:
            with suppress_stderr():
                frameset = pipeline.wait_for_frames(1000)
            if frameset is None:
                continue

            color_f = frameset.get_color_frame()
            depth_f = frameset.get_depth_frame()
            if not (color_f and depth_f):
                continue

            # --- Couleur ---
            w, h = color_f.get_width(), color_f.get_height()
            fmt = color_f.get_format()
            arr = np.frombuffer(color_f.get_data(), np.uint8)
            if fmt == ob.OBFormat.RGB:
                color = arr.reshape((h, w, 3))
                color = cv2.cvtColor(color, cv2.COLOR_RGB2BGR)
            elif fmt == ob.OBFormat.YUYV:
                color = arr.reshape((h, w, 2))
                color = cv2.cvtColor(color, cv2.COLOR_YUV2BGR_YUYV)
            else:
                color = np.zeros((h, w, 3), np.uint8)

            # --- Profondeur ---
            dw, dh = depth_f.get_width(), depth_f.get_height()
            depth = np.frombuffer(depth_f.get_data(), np.uint16).reshape((dh, dw))
            depth_vis = cv2.convertScaleAbs(depth, alpha=0.03)
            depth_vis = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)
            if depth_vis.shape[:2] != color.shape[:2]:
                depth_vis = cv2.resize(depth_vis, (color.shape[1], color.shape[0]), interpolation=cv2.INTER_NEAREST)

            combo = np.hstack((color, depth_vis))

            # --- FPS ---
            frame_count += 1
            if frame_count >= 10:
                now = time.time()
                fps = frame_count / (now - prev_time)
                prev_time = now
                frame_count = 0

            info = f"{w}x{h} {fmt.name}  FPS:{fps:.1f}"
            cv2.putText(combo, info, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (255, 255, 255), 2, cv2.LINE_AA)

            # --- Redimensionnement ---
            max_width = 1280
            scale = min(1.0, max_width / combo.shape[1])
            disp = combo
            if scale < 1.0:
                disp = cv2.resize(combo, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

            # --- Distance sous le curseur ---
            if 0 <= mouse_x < disp.shape[1] and 0 <= mouse_y < disp.shape[0]:
                full_x = int(mouse_x / scale)
                full_y = int(mouse_y / scale)
                if color.shape[1] <= full_x < combo.shape[1]:
                    dx = full_x - color.shape[1]
                    dy = full_y
                    if 0 <= dx < depth.shape[1] and 0 <= dy < depth.shape[0]:
                        distance_mm = int(depth[dy, dx])
                        text = f"{distance_mm} mm"
                        cv2.circle(disp, (mouse_x, mouse_y), 5, (0, 255, 255), 2)
                        cv2.putText(disp, text, (mouse_x + 10, mouse_y - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                    (0, 255, 255), 2, cv2.LINE_AA)

            # --- Capture avec espace ---
            key = cv2.waitKey(1) & 0xFF
            if key == 32:  # barre d’espace
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(str(out_dir / f"rgb_{ts}.png"), color)
                cv2.imwrite(str(out_dir / f"depth_{ts}.png"), depth_vis)
                np.save(out_dir / f"depth_raw_{ts}.npy", depth)
                print(f"[✓] Capture enregistrée : {ts}")

            if key == 27:  # Échap
                break

            cv2.imshow("RGB | Depth + FPS + Distance", disp)

    finally:
        with suppress_stderr():
            pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
