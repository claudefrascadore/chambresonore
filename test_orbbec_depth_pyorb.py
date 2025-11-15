#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# test_orbbec_depth_pyorb.py
# Test profondeur Orbbec Gemini 2 — robuste pour pyorbbecsdk 2.0.13 (Linux x86_64)
# S'adapte aux variations d'API (profils, accesseurs, buffers non contigus).
# ---------------------------------------------------------------------

import sys
import time
import numpy as np
import cv2

try:
    from pyorbbecsdk import Pipeline, Config, OBSensorType
except Exception as e:
    print("❌ pyorbbecsdk introuvable ou non chargeable :", e)
    sys.exit(1)

# ---------- Helpers d’introspection API ----------

def _has(obj, name):
    return hasattr(obj, name) and callable(getattr(obj, name))

def _get_whf(profile):
    """Retourne (w,h,fps) avec compatibilité des accesseurs."""
    w = profile.width()  if _has(profile, "width")  else profile.get_width()
    h = profile.height() if _has(profile, "height") else profile.get_height()
    f = profile.fps()    if _has(profile, "fps")    else profile.get_fps()
    return int(w), int(h), int(f)

def _frame_wh(frame):
    """Retourne (w,h) pour une frame, compat accesseurs."""
    w = frame.width()  if _has(frame, "width")  else frame.get_width()
    h = frame.height() if _has(frame, "height") else frame.get_height()
    return int(w), int(h)

def _profiles_count(profiles):
    """Compat: get_count() (confirmé chez toi) sinon count()/size()."""
    if _has(profiles, "get_count"):
        return int(profiles.get_count())
    if _has(profiles, "count"):
        return int(profiles.count())
    if _has(profiles, "size"):
        return int(profiles.size())
    raise RuntimeError("Liste de profils: aucune méthode de comptage disponible.")

def _profile_by_index(profiles, i):
    """Compat: get_stream_profile_by_index(i) ou get_profile(i)."""
    if _has(profiles, "get_stream_profile_by_index"):
        return profiles.get_stream_profile_by_index(i)
    if _has(profiles, "get_profile"):
        return profiles.get_profile(i)
    raise RuntimeError("Liste de profils: pas d’accès par index disponible.")

# ---------- Sélection du profil DEPTH ----------

def choose_depth_profile(pipeline):
    """
    Choisit un profil DEPTH valide. Préfère 640x480@30 si dispo, sinon le premier.
    API confirmée chez toi: pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
    puis get_count() et get_stream_profile_by_index(i).
    """
    try:
        profiles = pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
    except AttributeError:
        # Très vieux bindings : fallback sur un autre nom (peu probable ici)
        raise RuntimeError("OBSensorType.DEPTH_SENSOR indisponible dans cette build.")

    n = _profiles_count(profiles)
    if n == 0:
        raise RuntimeError("Aucun profil DEPTH disponible.")

    pick = None
    for i in range(n):
        p = _profile_by_index(profiles, i)
        w, h, f = _get_whf(p)
        if (w, h, f) == (640, 480, 30):
            return p
        if pick is None:
            pick = p
    return pick

# ---------- Conversion frame DEPTH -> image BGR ----------

def depth_frame_to_bgr(depth_frame, alpha=0.03):
    """
    Convertit la profondeur en fausses couleurs.
    Gère deux cas pour get_data():
      - renvoie déjà un ndarray (souvent non contigu) → on copie en contigu
      - renvoie un buffer/bytes → frombuffer()
    """
    w, h = _frame_wh(depth_frame)
    raw = depth_frame.get_data()

    if isinstance(raw, np.ndarray):
        # Copie contiguë + reshape sûr
        data = np.array(raw, dtype=np.uint16, copy=True).reshape((h, w))
    else:
        # bytes/memoryview/ctypes buffer
        arr = np.frombuffer(raw, dtype=np.uint16, count=h * w)
        data = arr.reshape((h, w))

    depth_8u = cv2.convertScaleAbs(data, alpha=alpha)
    return cv2.applyColorMap(depth_8u, cv2.COLORMAP_JET)

# ---------- Programme principal ----------

def main():
    print("Initialisation du pipeline Orbbec…")
    pipeline = Pipeline()
    config = Config()

    try:
        profile = choose_depth_profile(pipeline)
    except Exception as e:
        print("❌ Sélection du profil DEPTH impossible :", e)
        sys.exit(1)

    try:
        config.enable_stream(profile)
        pipeline.start(config)
        print("✅ Pipeline démarré (DEPTH). ESC pour quitter.")
    except Exception as e:
        print("❌ Démarrage du pipeline impossible :", e)
        sys.exit(1)

    t0 = time.time()
    frames = 0
    try:
        while True:
            fs = pipeline.wait_for_frames(100)  # timeout ms
            if not fs:
                continue

            depth = fs.get_depth_frame()
            if not depth:
                continue

            img = depth_frame_to_bgr(depth, alpha=0.03)
            cv2.imshow("Orbbec Gemini 2 – Depth", img)

            frames += 1
            if frames % 60 == 0:
                dt = max(time.time() - t0, 1e-6)
                print(f"~{frames/dt:.1f} FPS")

            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        try:
            pipeline.stop()
        except Exception:
            pass
        cv2.destroyAllWindows()
        print("✅ Capture terminée proprement.")

if __name__ == "__main__":
    main()

