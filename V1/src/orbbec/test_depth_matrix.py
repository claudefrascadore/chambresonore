import pyorbbecsdk as ob
import numpy as np

ctx = ob.Context()
devs = ctx.query_devices()
if len(devs) == 0:
    raise RuntimeError("Aucun appareil Orbbec détecté")

dev = devs[0]
info = dev.get_device_info()
cam_name = "Orbbec Gemini 2"
print(f"✅ Caméra détectée : {cam_name}")

# Capteur de profondeur
depth_sensor = dev.get_sensor(ob.OBSensorType.DEPTH_SENSOR)
profiles = depth_sensor.get_stream_profile_list()

count = 0
if hasattr(profiles, "get_count"):
    count = profiles.get_count()
elif hasattr(profiles, "__len__"):
    count = len(profiles)

if count == 0:
    raise RuntimeError("Aucun profil de flux disponible pour le capteur de profondeur")

selected = None
for i in range(count):
    try:
        prof = profiles.get_stream_profile_by_index(i)
        vp = prof.as_video_stream_profile()
        w, h, fmt, fps = vp.get_width(), vp.get_height(), vp.get_format(), vp.get_fps()
        print(f"Profil {i}: {w}x{h} {fmt} @ {fps} fps")
        if w == 640 and h == 480:
            selected = vp
            break
    except Exception as e:
        print(f"Profil {i}: erreur {e}")
        continue

if not selected:
    selected = profiles.get_stream_profile_by_index(0).as_video_stream_profile()

print(f"→ Profil choisi : {selected.get_width()}x{selected.get_height()} {selected.get_format()} @ {selected.get_fps()} fps")

pipeline = ob.Pipeline(dev)
config = ob.Config()
config.enable_stream(selected)
pipeline.start(config)

print("Lecture de 10 frames pour analyse des valeurs de profondeur...")
for i in range(10):
    fs = pipeline.wait_for_frames(1000)
    df = fs.get_depth_frame()
    if not df:
        print(f"Frame {i}: aucune donnée")
        continue
    data = np.frombuffer(df.get_data(), dtype=np.uint16)
    print(f"Frame {i}: min={data.min()}  max={data.max()}  moyenne={data.mean():.1f}")

pipeline.stop()
print("Terminé.")

