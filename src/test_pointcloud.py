from pyorbbecsdk import Pipeline, Config
import numpy as np

pipe = Pipeline()
cfg = Config()

cfg.enable_stream_color(640, 480, 30)
cfg.enable_stream_depth(640, 480, 30)

pipe.start(cfg)

try:
    print("→ Capture d'une frame...")
    frames = pipe.wait_for_frames(1000)

    depth = frames.get_depth_frame()
    color = frames.get_color_frame()

    print("Depth shape:", depth.get_height(), depth.get_width())
    print("Color shape:", color.get_height(), color.get_width())

    # Vérifier si la méthode existe
    if hasattr(depth, "to_pointcloud"):
        print("→ Méthode to_pointcloud disponible")
        pc = depth.to_pointcloud(color)
        points = pc.get_points()
        print("POINT CLOUD SHAPE:", points.shape)
        print("Sample:", points[:10])
    else:
        print("❌  depth.to_pointcloud() n'existe pas dans TA version locale.")

finally:
    pipe.stop()

