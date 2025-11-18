# -*- coding: utf-8 -*-
"""
orbbec_color_test.py — Diagnostic flux couleur Orbbec SDK 2.5.5
Version adaptée : SensorList.get_sensor(i) au lieu de get_value(i)
"""

import sys
import time
import traceback
import numpy as np

try:
    import pyorbbecsdk as ob
except ImportError:
    print("Erreur : pyorbbecsdk introuvable.")
    sys.exit(1)


def get_color_sensor(device):
    """Version finale : accède directement au capteur couleur."""
    try:
        s = device.get_sensor_by_type(ob.OBSensorType.COLOR_SENSOR)
        if s:
            print("✅ Capteur couleur trouvé via get_sensor_by_type()")
            return s
        print("⚠️ Aucun capteur couleur détecté (get_sensor_by_type a renvoyé None)")
        return None
    except Exception as e:
        print("⚠️ Erreur lors de l’accès au capteur couleur :", e)
        return None


def choose_profile(sensor):
    """Retourne un profil couleur valide (RGB/YUY/NV12)."""
    profiles = sensor.get_stream_profile_list()
    count = profiles.get_count()
    print("Profils disponibles :", count)
    best = None
    for i in range(count):
        try:
            # Compatibilité double API
            if hasattr(profiles, "get_profile"):
                p = profiles.get_profile(i)
            else:
                p = profiles.get_value(i)
            fmt = str(p.get_format())
            w = p.get_width()
            h = p.get_height()
            fps = p.get_fps()
            print(f"  [{i:02}] {fmt} {w}x{h}@{fps}")
            if best is None and any(x in fmt for x in ("RGB", "YUY", "NV12")) and w == 640 and h == 480:
                best = p
        except Exception as e:
            print(f"  [{i:02}] profil illisible:", e)
    if best is None and count > 0:
        print("Profil par défaut pris (index 0).")
        if hasattr(profiles, "get_profile"):
            best = profiles.get_profile(0)
        else:
            best = profiles.get_value(0)
    return best


def nv12_to_rgb(frame_nv12: np.ndarray, w: int, h: int) -> np.ndarray:
    y_size = w * h
    uv_size = y_size // 2
    y = frame_nv12[:y_size].reshape(h, w)
    uv = frame_nv12[y_size:y_size + uv_size].reshape(h // 2, w)
    u = uv[:, 0::2]
    v = uv[:, 1::2]
    u = np.repeat(np.repeat(u, 2, 0), 2, 1)
    v = np.repeat(np.repeat(v, 2, 0), 2, 1)
    y = y.astype(np.int16)
    u = u.astype(np.int16) - 128
    v = v.astype(np.int16) - 128
    r = y + 1.402 * v
    g = y - 0.344136 * u - 0.714136 * v
    b = y + 1.772 * u
    rgb = np.stack([r, g, b], -1)
    np.clip(rgb, 0, 255, out=rgb)
    return rgb.astype(np.uint8)


def save_ppm(path, rgb):
    h, w, _ = rgb.shape
    with open(path, "wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode())
        f.write(rgb.tobytes())


def main():
    try:
        try:
            print("Version SDK :", ob.get_version())
        except Exception:
            print("Version SDK : inconnue")

        pipe = ob.Pipeline()
        cfg = ob.Config()
        dev = pipe.get_device()
        print("Device :", dev)

        sensor = get_color_sensor(dev)
        if sensor is None:
            print("Abandon.")
            return 2

        prof = choose_profile(sensor)
        if prof is None:
            print("Aucun profil valide.")
            return 3

        cfg.enable_stream(prof)
        pipe.start(cfg)
        print("Pipeline démarré…")
        time.sleep(1.0)

        frameset = pipe.wait_for_frames(2000)
        if not frameset:
            print("⚠️ Aucun frameset reçu.")
            pipe.stop()
            return 4

        color = frameset.color_frame()
        if not color:
            print("⚠️ Aucun frame couleur.")
            pipe.stop()
            return 5

        w, h = color.get_width(), color.get_height()
        fmt = str(color.get_format())
        print(f"Frame couleur : {w}x{h} format={fmt}")
        data = np.frombuffer(color.get_data(), np.uint8)

        if "RGB" in fmt:
            rgb = data.reshape(h, w, 3)
        elif "NV12" in fmt:
            rgb = nv12_to_rgb(data, w, h)
        else:
            print("Format non géré :", fmt)
            pipe.stop()
            return 6

        out = "orbbec_color_test_out.ppm"
        save_ppm(out, rgb)
        print(f"✅ Image enregistrée {out}")
        pipe.stop()
        return 0

    except Exception:
        print("Erreur inattendue :")
        traceback.print_exc()
        return 10


if __name__ == "__main__":
    sys.exit(main())

