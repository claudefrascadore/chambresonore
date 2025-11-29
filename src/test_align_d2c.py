from pyorbbecsdk import Pipeline, OBSensorType, OBFormat, OBFrameType
import numpy as np
import time

pipe = Pipeline()

# Profondeur + Couleur
depth_profile = pipe.enable_depth_stream(width=640, height=400, fps=30)
color_profile = pipe.enable_color_stream(width=640, height=480, fps=30)

# Alignement logiciel profondeur → couleur
pipe.enable_align(OBFrameType.COLOR)

pipe.start()

print("Pipeline démarré (D2C actif)…")

for i in range(30):
    frameset = pipe.wait_for_frames(1000)

    depth = frameset.get_depth_frame()
    color = frameset.get_color_frame()
    aligned = frameset.get_frame(OBFrameType.DEPTH_ALIGNED_TO_COLOR)

    if depth is None or color is None or aligned is None:
        print("Frame manquante…")
        continue

    d = np.array(depth.get_data()).reshape(400, 640)
    c = np.array(color.get_data()).reshape(480, 640, 3)
    a = np.array(aligned.get_data()).reshape(480, 640)

    print(f"[{i}] depth={d.shape}, color={c.shape}, aligned={a.shape}")

pipe.stop()
print("Terminé.")

