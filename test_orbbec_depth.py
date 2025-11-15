#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test direct du flux de profondeur Orbbec Gemini 2 sous Linux.
Nécessite : OpenCV + NumPy + SDK Orbbec installé (libOrbbecSDK.so)
"""

import ctypes
import os
import sys
import cv2
import numpy as np
from ctypes import c_void_p, c_int, c_char_p, POINTER, byref

# --- Chargement du SDK ---
SDK_PATH = "/usr/local/lib/orbbec/libOrbbecSDK.so"
if not os.path.exists(SDK_PATH):
    print(f"❌ Bibliothèque introuvable : {SDK_PATH}")
    sys.exit(1)

try:
    ob = ctypes.cdll.LoadLibrary(SDK_PATH)
except Exception as e:
    print("Erreur au chargement du SDK :", e)
    sys.exit(1)

print("✅ SDK Orbbec chargé avec succès.")

# --- Initialisation du SDK ---
ob.obInit.argtypes = []
ob.obInit.restype = c_int
ob.obShutdown.argtypes = []

if ob.obInit() != 0:
    print("❌ Échec d'initialisation du SDK.")
    sys.exit(1)

print("✅ SDK initialisé.")

# --- Création du pipeline (caméra) ---
ob.obCreatePipeline.restype = c_void_p
pipeline = ob.obCreatePipeline()
if not pipeline:
    print("❌ Impossible de créer le pipeline caméra.")
    ob.obShutdown()
    sys.exit(1)

print("✅ Pipeline créé.")

# --- Démarrage du flux ---
ob.obStartPipeline.argtypes = [c_void_p]
ob.obStartPipeline(pipeline)
print("🎥 Flux démarré, récupération des trames...")

# --- Lecture en boucle ---
frame_count = 0
while True:
    # Obtenir la trame profondeur
    ob.obPipelineGetFrame.restype = c_void_p
    depth_frame = ob.obPipelineGetFrame(pipeline)

    if depth_frame:
        # Obtenir les dimensions
        width = ob.obFrameWidth(depth_frame)
        height = ob.obFrameHeight(depth_frame)
        data_ptr = ob.obFrameData(depth_frame)
        data_type = ctypes.c_uint16 * (width * height)
        data = np.ctypeslib.as_array(data_type.from_address(data_ptr))
        depth = data.reshape((height, width))

        # Normalisation et affichage
        depth_display = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX)
        depth_display = np.uint8(depth_display)
        cv2.imshow("Profondeur Gemini 2", depth_display)

    # Sortie avec ESC
    if cv2.waitKey(1) == 27:
        break

    frame_count += 1
    if frame_count % 30 == 0:
        print(f"{frame_count} trames reçues...")

# --- Nettoyage ---
ob.obStopPipeline(pipeline)
ob.obDeletePipeline(pipeline)
ob.obShutdown()
cv2.destroyAllWindows()
print("✅ Capture terminée proprement.")

