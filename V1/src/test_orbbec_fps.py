import cv2, time
import numpy as np
import pyorbbecsdk as ob

def main():
    pipeline = ob.Pipeline()
    config = ob.Config()

    # --- Profils de flux ---
    color_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)
    color_profile = color_profiles.get_video_stream_profile(1280, 720, ob.OBFormat.RGB, 30)
    config.enable_stream(color_profile)

    depth_profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
    depth_profile = depth_profiles.get_default_video_stream_profile()
    config.enable_stream(depth_profile)

    if hasattr(config, "set_frame_aggregate_output_mode"):
        config.set_frame_aggregate_output_mode(ob.OBFrameAggregateOutputMode.FULL_FRAME_REQUIRE)

    pipeline.start(config)

    prev_time = time.time()
    frame_count = 0
    fps = 0.0

    try:
        while True:
            frameset = pipeline.wait_for_frames(1000)
            if frameset is None:
                continue

            color_f = frameset.get_color_frame()
            depth_f = frameset.get_depth_frame()
            if not (color_f and depth_f):
                continue

            # --- Conversion couleur ---
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

            # --- Conversion profondeur ---
            dw, dh = depth_f.get_width(), depth_f.get_height()
            depth = np.frombuffer(depth_f.get_data(), np.uint16).reshape((dh, dw))
            depth_vis = cv2.convertScaleAbs(depth, alpha=0.03)
            depth_vis = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)
            if depth_vis.shape[:2] != color.shape[:2]:
                depth_vis = cv2.resize(depth_vis, (color.shape[1], color.shape[0]), interpolation=cv2.INTER_NEAREST)

            combo = np.hstack((color, depth_vis))

            # --- Calcul FPS ---
            frame_count += 1
            if frame_count >= 10:
                now = time.time()
                fps = frame_count / (now - prev_time)
                prev_time = now
                frame_count = 0

            # --- Overlay infos ---
            info = f"{w}x{h} {fmt.name}  FPS:{fps:.1f}"
            cv2.putText(combo, info, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

            # --- Redimensionnement automatique ---
            max_width = 1280
            scale = min(1.0, max_width / combo.shape[1])
            if scale < 1.0:
                combo = cv2.resize(combo, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

            cv2.imshow("RGB | Depth + FPS", combo)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
