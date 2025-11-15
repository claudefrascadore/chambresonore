# Auto-généré par Codex le {DATE}
# -------------------------------------------------------------
# orbbec.rgb_depth_viewer
# Affiche côte à côte les flux RGB et profondeur de l'Orbbec Gemini 2
# Compatible avec pyorbbecsdk v2.0.13 (Linux x86_64)
# -------------------------------------------------------------

import cv2
import numpy as np
from pyorbbecsdk import Pipeline, Config, OBSensorType

def to_bgr(depth_frame):
    """Convertit une trame profondeur en image colorisée."""
    h, w = depth_frame.get_height(), depth_frame.get_width()
    data = np.frombuffer(depth_frame.get_data(), dtype=np.uint16).reshape(h, w)
    depth_8u = cv2.convertScaleAbs(data, alpha=0.03)
    return cv2.applyColorMap(depth_8u, cv2.COLORMAP_JET)

def main():
    print("Initialisation du pipeline Orbbec (RGB + Depth)…")
    pipeline = Pipeline()
    config = Config()

    try:
        profiles_depth = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
        profiles_color = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)

        depth_profile = profiles_depth.get_default_video_stream_profile()
        color_profile = profiles_color.get_default_video_stream_profile()

        config.enable_stream(depth_profile)
        config.enable_stream(color_profile)
        pipeline.start(config)
        print("✅ Flux synchronisé démarré. Appuie sur ESC pour quitter.")
    except Exception as e:
        print("❌ Erreur lors du démarrage du pipeline :", e)
        return

    try:
        while True:
            frameset = pipeline.wait_for_frames(100)
            if not frameset:
                continue

            depth_frame = frameset.get_depth_frame()
            color_frame = frameset.get_color_frame()
            if not depth_frame or not color_frame:
                continue

            color_img = np.frombuffer(color_frame.get_data(), dtype=np.uint8).reshape(
                color_frame.get_height(), color_frame.get_width(), 3
            )
            color_img = cv2.cvtColor(color_img, cv2.COLOR_RGB2BGR)
            depth_img = to_bgr(depth_frame)

            # Ajuste la taille du flux profondeur pour correspondre à la couleur
            depth_resized = cv2.resize(depth_img, (color_img.shape[1], color_img.shape[0]))
            stacked = np.hstack((color_img, depth_resized))

            cv2.imshow("Orbbec Gemini 2 – RGB + Depth", stacked)
            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        pipeline.stop()
        cv2.destroyAllWindows()
        print("✅ Capture terminée proprement.")

if __name__ == "__main__":
    main()

