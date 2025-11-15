# -*- coding: utf-8 -*-
"""
camera_view.py
Affiche un flux UVC (OpenCV) et colore automatiquement la profondeur.
- flux couleur : affiché normalement
- flux profondeur (si force_gray=True) : converti en pseudo-couleur (COLORMAP_TURBO)
"""

import os
import cv2
import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel

__all__ = ["UvcView"]


def _probe_device(path, width, height, fps):
    """
    Tente d'ouvrir un device V4L2 donné et de lire une frame.
    Retourne (cap, frame) si ça fonctionne, sinon (None, None).
    """
    cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
    if not cap.isOpened():
        return None, None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    ret, frame = cap.read()
    if not ret or frame is None:
        cap.release()
        return None, None
    return cap, frame


class UvcView(QLabel):
    """
    Widget vidéo générique pour un flux UVC.

    Paramètres (compatibles avec grid_ui.GridUI) :
      - device         : chemin du device V4L2 (ex. "/dev/video4" ou "/dev/video0")
      - cap_width      : résolution capturée (largeur)
      - cap_height     : résolution capturée (hauteur)
      - fps            : fréquence cible
      - display_width  : largeur d'affichage (redimensionnée)
      - display_height : hauteur d'affichage (redimensionnée)
      - force_gray     : si True, convertit en fausses couleurs (vue type profondeur)
    """

    def __init__(
        self,
        device="/dev/video4",
        cap_width=640,
        cap_height=480,
        fps=30,
        display_width=None,
        display_height=None,
        force_gray=False,
        parent=None,
    ):
        super().__init__(parent)

        self.requested_device = device
        self.device = device
        self.cap_width = cap_width
        self.cap_height = cap_height
        self.fps = fps
        self.force_gray = force_gray
        self.display_width = display_width or cap_width
        self.display_height = display_height or cap_height

        self.cap = None

        # 1) Essayer d'abord le device demandé
        cap, frame = _probe_device(self.requested_device, self.cap_width, self.cap_height, self.fps)
        if cap is not None:
            self.cap = cap
            self.device = self.requested_device
            print(
                f"🎥 Flux UVC actif sur {self.device} "
                f"({frame.shape[1]}x{frame.shape[0]} @ {self.fps}fps) [device demandé]"
            )
        else:
            print(f"⚠️ Impossible d’ouvrir {self.requested_device}. Recherche automatique d’un device valide…")
            # 2) Scan automatique /dev/video0 à /dev/video9
            for i in range(10):
                path = f"/dev/video{i}"
                if not os.path.exists(path):
                    continue
                cap2, frame2 = _probe_device(path, self.cap_width, self.cap_height, self.fps)
                if cap2 is not None:
                    self.cap = cap2
                    self.device = path
                    print(
                        f"✅ Device auto-sélectionné : {self.device} "
                        f"({frame2.shape[1]}x{frame2.shape[0]} @ {self.fps}fps)"
                    )
                    break

        if self.cap is None:
            print("❌ Aucun device vidéo utilisable trouvé. UvcView restera noir.")
        else:
            # On mémorise la dernière frame lue au probe pour éviter un premier écran noir
            self._last_frame_shape = (self.display_height, self.display_width, 3)

        # QLabel
        self.setFixedSize(self.display_width, self.display_height)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background:black;border:1px solid gray;")

        # Timer de rafraîchissement
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_frame)
        self._timer.start(int(1000 / max(1, self.fps)))

    def update_frame(self):
        """Lit une frame et l'affiche, avec conversion éventuelle en pseudo-couleur."""
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        # Si on force une vue "profondeur" pseudo-colorée
        if self.force_gray:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            colorized = cv2.applyColorMap(gray, cv2.COLORMAP_TURBO)
            rgb = cv2.cvtColor(colorized, cv2.COLOR_BGR2RGB)
        else:
            # Cas normal : flux couleur BGR → RGB
            if len(frame.shape) == 2 or frame.shape[2] == 1:
                gray = frame if len(frame.shape) == 2 else frame[:, :, 0]
                colorized = cv2.applyColorMap(gray, cv2.COLORMAP_TURBO)
                rgb = cv2.cvtColor(colorized, cv2.COLOR_BGR2RGB)
            else:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        rgb_disp = cv2.resize(
            rgb,
            (self.display_width, self.display_height),
            interpolation=cv2.INTER_AREA,
        )
        h, w, ch = rgb_disp.shape
        qimg = QImage(
            rgb_disp.data,
            w,
            h,
            ch * w,
            QImage.Format.Format_RGB888,
        )
        self.setPixmap(QPixmap.fromImage(qimg))

    def close(self):
        """Libère proprement la capture vidéo."""
        if self.cap and self.cap.isOpened():
            self.cap.release()

