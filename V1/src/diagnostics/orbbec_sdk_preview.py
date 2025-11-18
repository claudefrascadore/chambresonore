#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/diagnostics/orbbec_sdk_preview.py

Test simple du SDK Orbbec (pyorbbecsdk) pour la Gemini 2 :
- ouvre un Pipeline Orbbec
- active un flux couleur et un flux profondeur
- affiche les deux côte à côte dans une fenêtre OpenCV
- utilise uniquement le SDK Orbbec (aucun accès direct /dev/videoX)

Touche 'q' pour quitter.
"""

import sys
import time

from typing import Optional

import cv2
import numpy as np

import pyorbbecsdk as ob


def simple_color_to_bgr(frame: "ob.ColorFrame") -> Optional[np.ndarray]:
    """
    Convertit un ColorFrame Orbbec (RGB) en image BGR pour OpenCV.

    Retourne:
        np.ndarray (H, W, 3) en BGR, ou None si la taille des données ne correspond pas.
    """
    width = frame.get_width()
    height = frame.get_height()
    data = np.frombuffer(frame.get_data(), dtype=np.uint8)

    # On s’attend à 3 canaux (RGB)
    if data.size != width * height * 3:
        return None

    rgb = data.reshape((height, width, 3))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


def depth_to_colormap(frame: "ob.DepthFrame",
                      min_depth_mm: int = 150,
                      max_depth_mm: int = 2000) -> np.ndarray:
    """
    Convertit un DepthFrame Orbbec en image couleur pseudo-codée (colormap).

    Arguments:
        frame        : ob.DepthFrame
        min_depth_mm : profondeur minimale (en mm) pour le clipping
        max_depth_mm : profondeur maximale (en mm) pour le clipping

    Retourne:
        np.ndarray (H, W, 3) en BGR (image colorisée).
    """
    width = frame.get_width()
    height = frame.get_height()
    # Les profondeurs sont en uint16
    depth_data = np.frombuffer(frame.get_data(), dtype=np.uint16).reshape((height, width))

    # On clippe dans [min_depth_mm, max_depth_mm]
    depth_clipped = np.clip(depth_data, min_depth_mm, max_depth_mm)

    # On inverse pour que les zones proches soient plus claires (optionnel)
    depth_inverted = max_depth_mm - depth_clipped

    # Normalisation dans [0, 255]
    depth_normalized = cv2.normalize(
        depth_inverted,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    ).astype(np.uint8)

    # Application d’une colormap (Magma ou autre)
    depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_MAGMA)

    return depth_colored


def choose_color_profile(pipeline: "ob.Pipeline") -> "ob.VideoStreamProfile":
    """
    Choisit un profil couleur RGB pour la caméra.

    Stratégie:
        1. On essaie RGB 640x480 @ 30
        2. Sinon, on prend le premier profil en RGB
        3. Si rien en RGB, on tombe en erreur
    """
    profiles = pipeline.get_stream_profile_list(ob.OBSensorType.COLOR_SENSOR)

    # On commence par chercher un profil RGB 640x480@30
    candidate = None
    for p in profiles:
        if (p.get_format() == ob.OBFormat.RGB and
                p.get_width() == 640 and
                p.get_height() == 480 and
                p.get_fps() == 30):
            candidate = p
            break

    if candidate is not None:
        print("Profil couleur sélectionné : RGB 640x480 @ 30")
        return candidate

    # Sinon, premier profil RGB disponible
    for p in profiles:
        if p.get_format() == ob.OBFormat.RGB:
            candidate = p
            print(
                "Profil couleur (fallback) : RGB "
                f"{p.get_width()}x{p.get_height()} @ {p.get_fps()}"
            )
            return candidate

    raise RuntimeError("Aucun profil couleur RGB disponible sur cette caméra.")


def choose_depth_profile(pipeline: "ob.Pipeline") -> "ob.VideoStreamProfile":
    """
    Choisit un profil profondeur pour la caméra.

    Stratégie:
        1. On essaie Y16 640x400 @ 30 (idéal pour Gemini 2)
        2. Sinon, on prend le profil vidéo par défaut
    """
    profiles = pipeline.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)

    candidate = None
    for p in profiles:
        if (p.get_format() == ob.OBFormat.Y16 and
                p.get_width() == 640 and
                p.get_height() == 400 and
                p.get_fps() == 30):
            candidate = p
            print("Profil profondeur sélectionné : Y16 640x400 @ 30")
            break

    if candidate is not None:
        return candidate

    # Fallback : profil vidéo par défaut
    try:
        default_profile = profiles.get_default_video_stream_profile()
        print(
            "Profil profondeur (fallback) : "
            f"{default_profile.get_format()} "
            f"{default_profile.get_width()}x{default_profile.get_height()} "
            f"@ {default_profile.get_fps()}"
        )
        return default_profile
    except Exception:
        raise RuntimeError("Impossible d’obtenir un profil profondeur par défaut.")


def main() -> int:
    """
    Point d’entrée principal.

    Ouvre le pipeline Orbbec, configure couleur + profondeur,
    et affiche les deux flux côte à côte.
    """
    try:
        print("Initialisation du SDK Orbbec…")
        pipeline = ob.Pipeline()
        config = ob.Config()

        # Sélection des profils
        color_profile = choose_color_profile(pipeline)
        depth_profile = choose_depth_profile(pipeline)

        # Activation des flux
        config.enable_stream(color_profile)
        config.enable_stream(depth_profile)

        # Alignement matériel couleur/profondeur
        try:
            config.set_align_mode(ob.OBAlignMode.HW_MODE)
            pipeline.enable_frame_sync()
            print("Alignement D2C matériel activé (HW_MODE).")
        except Exception as e:
            print("Impossible d’activer l’alignement matériel D2C :", e)

        # Démarrage du pipeline
        pipeline.start(config)
        print("Pipeline Orbbec démarré.")

        # Boucle principale
        while True:
            frames = pipeline.wait_for_frames(100)
            if frames is None:
                continue

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            if color_frame is None or depth_frame is None:
                continue

            color_img = simple_color_to_bgr(color_frame)
            if color_img is None:
                continue

            depth_img = depth_to_colormap(depth_frame)

            # On met les deux images à la même taille pour concaténer
            if color_img.shape[:2] != depth_img.shape[:2]:
                depth_img = cv2.resize(
                    depth_img,
                    (color_img.shape[1], color_img.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                )

            concat = cv2.hconcat([color_img, depth_img])

            # Mise à l’échelle pour ne pas remplir tout l’écran
            scale = 0.7
            concat = cv2.resize(
                concat,
                (0, 0),
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_LINEAR
            )

            cv2.imshow("Orbbec SDK - Couleur (gauche) / Profondeur (droite)", concat)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

        return 0

    except KeyboardInterrupt:
        return 0

    except Exception as e:
        print("Erreur dans orbbec_sdk_preview :", e)
        return 1

    finally:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            # Si le pipeline existe encore dans la portée
            # Python fermera de toute façon à la sortie.
            pass
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

