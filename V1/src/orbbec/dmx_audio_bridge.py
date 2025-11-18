#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chambre sonore — Phase 3
Module : orbbec.dmx_audio_bridge

Pont TEMPS RÉEL :
  Orbbec Gemini 2 → matrice 6×6 → DMX (OLA) + Audio (pygame)

Caractéristiques :
  - Capteur réel 'gemini2' via SDK Python Orbbec.
  - Refus de démarrer si le capteur est demandé mais indisponible.
  - DMX via OLA (conversion corrigée).
  - Audio via pygame (ou simulation).
  - Config JSON automatique.
  - Affichage console 6×6 (--show-grid).
  - Arrêt propre (SIGINT/SIGTERM).
"""

from __future__ import annotations
import argparse, json, math, os, signal, sys, threading, time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------
# Dépendances optionnelles
# ---------------------------------------------------------------------

HAS_OLA = False
try:
    from ola.ClientWrapper import ClientWrapper  # type: ignore
    HAS_OLA = True
except Exception:
    pass

HAS_PYGAME = False
try:
    import pygame  # type: ignore
    HAS_PYGAME = True
except Exception:
    pass


def _try_import_orbbec_sdk():
    candidates = ("pyorbbecsdk", "orbbecsdk", "orbbec")
    last_err = None
    for name in candidates:
        try:
            mod = __import__(name)
            return name, mod
        except Exception as e:
            last_err = e
    return None, last_err


# ---------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------

MATRIX_ROWS = 6
MATRIX_COLS = 6
DMX_SLOTS = 512


def db_to_linear(db: float) -> float:
    return math.pow(10.0, db / 20.0)


def rc_key(r: int, c: int) -> str:
    return f"{r},{c}"


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


# ---------------------------------------------------------------------
# Capteur Orbbec Gemini 2
# ---------------------------------------------------------------------

class SensorProviderGemini2:
    def __init__(self, module_name: str, sdk_mod,
                 rows: int = MATRIX_ROWS, cols: int = MATRIX_COLS,
                 preferred_width: int = 1200, 
                 preferred_height: int = 800,
                 preferred_fps: int = 10):
        self.rows, self.cols = rows, cols
        self.w, self.h, self.fps = preferred_width, preferred_height, preferred_fps
        self._sdk_name = module_name
        self._sdk = sdk_mod
        self._pipe = None
        self._timeouts = 0
        self._setup_pipeline()

    # ---------- configuration robuste du pipeline ----------
    def _setup_pipeline(self) -> None:
        m = self._sdk
        try:
            ctx = m.Context()
            devs = ctx.query_devices()
            if not devs:
                raise RuntimeError("Aucun périphérique Orbbec détecté.")
            dev = devs[0]
            # infos appareil
            try:
                info = dev.get_device_info()
                name = getattr(info, "get_name", getattr(info, "name", lambda: "<inconnu>"))()
                sn = getattr(info, "get_serial_number", getattr(info, "serial_number", lambda: "?"))()
                fw = getattr(info, "get_firmware_version", getattr(info, "firmware_version", lambda: "?"))()
            except Exception:
                name, sn, fw = "<inconnu>", "?", "?"
            print(f"✅ Caméra : {name} — SN {sn} — FW {fw}")

            # pipeline + config
            self._pipe = m.Pipeline(dev) if hasattr(m, "Pipeline") else m.Pipeline()
            cfg = m.Config()

            # type de capteur
            sensor_type = None
            if hasattr(m, "OBSensorType") and hasattr(m.OBSensorType, "DEPTH_SENSOR"):
                sensor_type = m.OBSensorType.DEPTH_SENSOR
            for cand in ("OBSensorType_DEPTH", "DEPTH_SENSOR", "DEPTH"):
                if sensor_type is None and hasattr(m, cand):
                    sensor_type = getattr(m, cand)
            if sensor_type is None:
                raise RuntimeError("Type de capteur profondeur introuvable.")
            depth_sensor = dev.get_sensor(sensor_type)

            profiles = depth_sensor.get_stream_profile_list()
            count = profiles.get_count()
            prof = None
            # tentative standard
            try:
                if hasattr(m, "OBFormat") and hasattr(m.OBFormat, "Y16"):
                    prof = profiles.get_video_stream_profile(self.w, self.h, m.OBFormat.Y16, self.fps)
            except Exception:
                prof = None
            # fallback : exploration manuelle
            if prof is None:
                getters = [
                    "get_video_stream_profile_by_index",
                    "get_stream_profile_by_index",
                    "get_profile_by_index",
                    "get_profile",
                    "get_stream_profile"
                ]
                chosen = None
                for i in range(count):
                    for g in getters:
                        if hasattr(profiles, g):
                            try:
                                p = getattr(profiles, g)(i)
                                if hasattr(p, "get_width") and hasattr(p, "get_height"):
                                    chosen = p
                                    break
                            except Exception:
                                pass
                    if chosen:
                        break
                if chosen is None:
                    raise RuntimeError("Aucun profil vidéo exploitable.")
                prof = chosen
                try:
                    print(f"⚠️ Profil défaut : {prof.get_width()}×{prof.get_height()} @ {prof.get_fps()} fps")
                except Exception:
                    print("⚠️ Profil défaut sélectionné.")
            try:
                # Met à jour les dimensions selon le profil sélectionné
                self.w = prof.get_width()
                self.h = prof.get_height()
                self.fps = getattr(prof, "get_fps", lambda: self.fps)()
                print(f"ℹ️ Profil retenu : {self.w}×{self.h} @ {self.fps} fps")
            except Exception:
                pass

            cfg.enable_stream(prof)
            self._pipe.start(cfg)
            print("✅ Pipeline Orbbec initialisé avec succès.")
        except Exception as e:
            raise RuntimeError(f"Échec initialisation Orbbec : {e}")

    # ---------- acquisition ----------
    def _acquire_depth_mm(self) -> Optional[memoryview]:
        m = self._sdk
        if self._pipe is None:
            return None
        frames = self._pipe.wait_for_frames(100)  # Timeout 100 ms (au lieu de 1000)
        if not frames:
            self._timeouts += 1
            if (self._timeouts % 10) == 0:
                print(f"[SENSOR] timeout ({self._timeouts})")
            return None
        get_depth = getattr(frames, "get_depth_frame", None)
        if not get_depth:
            return None
        d = get_depth()
        if not d:
            return None
        data = None
        for attr in ("get_data", "data", "get_buffer"):
            if hasattr(d, attr):
                try:
                    data = getattr(d, attr)()
                    break
                except Exception:
                    pass
        if data is None:
            return None
        try:
            return memoryview(data)
        except TypeError:
            return memoryview(bytes(data))

    # ---------- lecture logique 6×6 ----------
    def read_active_cells(self, threshold_mm: int) -> List[Tuple[int, int]]:
        buf = self._acquire_depth_mm()
        if buf is None:
            return []
        w, h = self.w, self.h
        if len(buf) < (w * h * 2):
            return []
        mv = buf.cast("H")
        cells: List[Tuple[int, int]] = []
        cw, ch = max(1, w // MATRIX_COLS), max(1, h // MATRIX_ROWS)
        for r in range(MATRIX_ROWS):
            for c in range(MATRIX_COLS):
                x0, y0 = c * cw, r * ch
                xs = [x0, min(x0 + cw // 2, w - 1)]
                ys = [y0, min(y0 + ch // 2, h - 1)]
                acc = 0
                for yy in ys:
                    base = yy * w
                    for xx in xs:
                        acc += mv[base + xx]
                mean_mm = acc // max(1, len(xs) * len(ys))
                if 0 < mean_mm < threshold_mm:
                    cells.append((r, c))
        return cells

    def shutdown(self) -> None:
        try:
            if self._pipe is not None and hasattr(self._pipe, "stop"):
                self._pipe.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------
# DMX
# ---------------------------------------------------------------------

class DMXOutput:
    def __init__(self, universe: int = 1, verbose: bool = False):
        self.universe, self._verbose = universe, verbose
        self.buffer = bytearray([0] * DMX_SLOTS)
        self._lock = threading.Lock()
        self._simulated = not HAS_OLA
        self._send_errors = 0
        if HAS_OLA:
            try:
                self._wrapper = ClientWrapper()
                self._client = self._wrapper.Client()
            except Exception as e:
                print(f"[DMX][OLA] init erreur : {e}")
                self._simulated = True
        print(f"[DMX] Mode : {'OLA' if not self._simulated else 'SIMULATION'}, univers={self.universe}")

    def set_channels_for_cell(self, address: int, values: List[int]) -> None:
        with self._lock:
            start = max(0, address - 1)
            for i, v in enumerate(values):
                idx = start + i
                if 0 <= idx < DMX_SLOTS:
                    self.buffer[idx] = max(0, min(255, int(v)))

    def flush(self) -> None:
        if self._simulated:
            if self._verbose:
                nz = [i + 1 for i, v in enumerate(self.buffer) if v]
                print(f"[DMX][SIM] push : {len(nz)} ch actifs : {nz[:12]}")
            return
        import array
        data = array.array('B', self.buffer)
        try:
            self._client.SendDmx(self.universe, data, lambda state: None)
            # IMPORTANT: ne JAMAIS appeler Run() (bloquant).
            if hasattr(self._wrapper, "RunOnce"):
                self._wrapper.RunOnce()
            # Sinon, on ne fait rien: l’OLA s’en sortira au tick suivant.
        except Exception as e:
            self._send_errors += 1
            print(f"[DMX][OLA] Erreur : {e} (#{self._send_errors})")
            if self._send_errors > 5:
                print("[DMX][OLA] Passage en mode simulation.")
                self._simulated = True

    def blackout(self) -> None:
        with self._lock:
            for i in range(DMX_SLOTS):
                self.buffer[i] = 0
        self.flush()


# ---------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------

class AudioEngine:
    def __init__(self, enabled, max_voices, gain_db, attack_ms, release_ms):
        self.enabled = enabled and HAS_PYGAME
        self.gain = db_to_linear(gain_db)
        self.attack, self.release = int(attack_ms), int(release_ms)
        self.max_voices = max(1, int(max_voices))
        self._channels, self._sounds, self._active = {}, {}, set()
        if self.enabled:
            try:
                pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=1024)
                pygame.init()
                pygame.mixer.set_num_channels(self.max_voices)
                print(f"[AUDIO] pygame OK : {self.max_voices} voix, gain {self.gain:.3f}")
            except Exception as e:
                print(f"[AUDIO] init échec : {e}")
                self.enabled = False
        else:
            print("[AUDIO] Mode simulation")

    def load_cell_sound(self, key: str, path: Optional[str]):
        if not self.enabled or not path or not os.path.isfile(path):
            self._sounds[key] = None
            return
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(self.gain)
            self._sounds[key] = snd
        except Exception as e:
            print(f"[AUDIO] Erreur chargement {path} : {e}")
            self._sounds[key] = None

    def note_on(self, key: str):
        if key in self._active:
            return
        self._active.add(key)
        if not self.enabled:
            print(f"[AUDIO][SIM] ON {key}")
            return
        snd = self._sounds.get(key)
        if not snd:
            return
        ch = pygame.mixer.find_channel()
        if not ch:
            ch = pygame.mixer.Channel(0)
        ch.play(snd, loops=-0, fade_ms=self.attack)
        ch.set_volume(self.gain)
        self._channels[key] = ch

    def note_off(self, key: str):
        if key not in self._active:
            return
        self._active.discard(key)
        if not self.enabled:
            print(f"[AUDIO][SIM] OFF {key}")
            return
        ch = self._channels.get(key)
        if ch:
            ch.fadeout(self.release)

    def shutdown(self):
        if self.enabled:
            pygame.mixer.stop()
            pygame.quit()


# ---------------------------------------------------------------------
# Mapping DMX + Config
# ---------------------------------------------------------------------

@dataclass
class DMXMapping:
    universe: int
    base_address: int
    channels_per_cell: int
    cell_layout: str = "row-major"

    def address_of(self, r: int, c: int) -> int:
        idx = r * MATRIX_COLS + c if self.cell_layout == "row-major" else c * MATRIX_ROWS + r
        return self.base_address + idx * self.channels_per_cell


@dataclass
class BridgeConfig:
    dmx: DMXMapping
    depth_threshold_mm: int
    audio_enabled: bool
    audio_voice_stealing: bool
    audio_max_voices: int
    audio_gain_db: float
    audio_attack_ms: int
    audio_release_ms: int
    audio_files: Dict[str, Optional[str]] = field(default_factory=dict)

    @staticmethod
    def load_or_create(path: str) -> "BridgeConfig":
        DEFAULT = {
            "dmx": {"universe": 1, "base_address": 1, "channels_per_cell": 3, "cell_layout": "row-major"},
            "depth": {"threshold_mm": 2200},
            "audio": {"enabled": True, "voice_stealing": True, "max_voices": 12,
                      "gain_db": -6.0, "attack_ms": 5, "release_ms": 120, "files": {}}
        }
        if not os.path.isfile(path):
            ensure_parent_dir(path)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT, f, indent=2)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        dmx = data.get("dmx", {})
        depth, audio = data.get("depth", {}), data.get("audio", {})
        mapping = DMXMapping(
            universe=int(dmx.get("universe", 1)),
            base_address=int(dmx.get("base_address", 1)),
            channels_per_cell=int(dmx.get("channels_per_cell", 3)),
            cell_layout=str(dmx.get("cell_layout", "row-major")),
        )
        return BridgeConfig(
            dmx=mapping,
            depth_threshold_mm=int(depth.get("threshold_mm", 2200)),
            audio_enabled=bool(audio.get("enabled", True)),
            audio_voice_stealing=bool(audio.get("voice_stealing", True)),
            audio_max_voices=int(audio.get("max_voices", 12)),
            audio_gain_db=float(audio.get("gain_db", -6.0)),
            audio_attack_ms=int(audio.get("attack_ms", 5)),
            audio_release_ms=int(audio.get("release_ms", 120)),
            audio_files=audio.get("files", {}),
        )


# ---------------------------------------------------------------------
# Pont principal
# ---------------------------------------------------------------------

class DMXAudioBridge:
    def __init__(self, cfg: BridgeConfig, fps: int, sensor_kind: str,
                 show_grid: bool, verbose_dmx: bool):
        self.cfg, self.fps, self._show_grid = cfg, max(1, int(fps)), show_grid
        self.period = 1.0 / self.fps
        name, mod_or_err = _try_import_orbbec_sdk()
        if not name:
            print("❌ SDK Orbbec Python introuvable.")
            sys.exit(2)
        self.sensor = SensorProviderGemini2(name, mod_or_err)
        print(f"[SENSOR] Orbbec Gemini 2 via '{name}'")
        self.dmx = DMXOutput(cfg.dmx.universe, verbose_dmx)
        self.audio = AudioEngine(cfg.audio_enabled, cfg.audio_max_voices,
                                 cfg.audio_gain_db, cfg.audio_attack_ms, cfg.audio_release_ms)
        self.state = [[False]*MATRIX_COLS for _ in range(MATRIX_ROWS)]
        # Compteurs anti-rebond : nombre de frames consécutives actives/inactives
        self._on_count  = [[0]*MATRIX_COLS for _ in range(MATRIX_ROWS)]
        self._off_count = [[0]*MATRIX_COLS for _ in range(MATRIX_ROWS)]
        # Seuils : ajustables
        self._ACTIVATE_N   = 3   # frames actives d’affilée pour déclencher
        self._DEACTIVATE_N = 6   # frames inactives d’affilée pour relâcher

        for r in range(MATRIX_ROWS):
            for c in range(MATRIX_COLS):
                self.audio.load_cell_sound(rc_key(r, c), cfg.audio_files.get(rc_key(r, c)))

        self._stop = threading.Event()
    def _apply_cell_to_dmx(self, r, c, active):
        addr = self.cfg.dmx.address_of(r, c)
        vals = [255, 50, 0] if active else [0, 0, 0]
        self.dmx.set_channels_for_cell(addr, vals)

    def _apply_cell_to_audio(self, r, c, active):
        key = rc_key(r, c)
        (self.audio.note_on if active else self.audio.note_off)(key)

    def _update_from_active_cells(self, active_cells: List[Tuple[int, int]]) -> None:
        """Applique un anti-rebond : N frames actives pour ON, M frames inactives pour OFF."""
        active_set = set(active_cells)
        for r in range(MATRIX_ROWS):
            for c in range(MATRIX_COLS):
                was = self.state[r][c]
                is_active_now = (r, c) in active_set

                if is_active_now:
                    # cellule "vue" active à cette frame
                    self._on_count[r][c]  = min(self._on_count[r][c] + 1, 255)
                    self._off_count[r][c] = 0
                    # déclenche si on était OFF et qu’on a empilé assez de frames actives
                    if not was and self._on_count[r][c] >= self._ACTIVATE_N:
                        self.state[r][c] = True
                        self._apply_cell_to_audio(r, c, True)   # NOTE ON (one-shot si loops=0)
                else:
                    # cellule "vue" inactive à cette frame
                    self._off_count[r][c] = min(self._off_count[r][c] + 1, 255)
                    self._on_count[r][c]  = 0
                    # relâche si on était ON et qu’on a cumulé assez d’inactives
                    if was and self._off_count[r][c] >= self._DEACTIVATE_N:
                        self.state[r][c] = False
                        self._apply_cell_to_audio(r, c, False)  # NOTE OFF (fadeout)

                # DMX suit l’état filtré (pas la mesure brute)
                self._apply_cell_to_dmx(r, c, self.state[r][c])

    import sys

    def _print_grid(self, cells):
        """Affiche une matrice 6×6 fixe, rafraîchie sur place (sans défilement)."""
        if not self._show_grid:
            return
        grid = [["●" if (r, c) in cells else "·" for c in range(MATRIX_COLS)] for r in range(MATRIX_ROWS)]
        sys.stdout.write("\033[H\033[J")  # efface l’écran (clear)
        sys.stdout.write("[Chambre sonore — matrice 6×6]\n")
        for r in range(MATRIX_ROWS):
            sys.stdout.write(" ".join(grid[r]) + "\n")
            sys.stdout.write(f"-----------\nActives: {len(cells)}\n")
            sys.stdout.flush()

    def run(self) -> None:
        """Boucle principale du pont : lecture capteur → MAJ DMX/Audio → affichage grille."""
        print(f"[BRIDGE] Démarrage à {self.fps} fps, seuil={self.cfg.depth_threshold_mm} mm.")
        next_t = time.monotonic()
        loop_count = 0
        try:
            while not self._stop.is_set():
                loop_count += 1
       
                # 1) Lecture des cellules actives (robuste aux exceptions sensor)
                try:
                    cells = self.sensor.read_active_cells(self.cfg.depth_threshold_mm)
                except Exception as e:
                    print(f"[SENSOR] erreur: {e}")
                    cells = []

                # 2) Application état → DMX + Audio
                self._update_from_active_cells(cells)

                # 3) Envoi DMX (non bloquant); OLA RunOnce seulement si dispo
                self.dmx.flush()

                # 4) Affichage de la grille en console (si demandé)
                self._print_grid(cells)

                # 5) Heartbeat périodique pour confirmer que la boucle vit
                if (loop_count % self.fps) == 0:
                    print(f"[BRIDGE] tick {loop_count}")
                sys.stdout.flush()

                # 6) Cadence : on essaie de respecter self.fps sans bloquer indéfiniment
                next_t += self.period
                delay = next_t - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                else:
                    # on a du retard : on recale pour éviter l’effet « rattrapage »
                    next_t = time.monotonic()
        finally:
            self.shutdown()

    def shutdown(self):
        print("[BRIDGE] Arrêt…")
        for r in range(MATRIX_ROWS):
            for c in range(MATRIX_COLS):
                self._apply_cell_to_audio(r, c, False)
        self.dmx.blackout()
        self.sensor.shutdown()
        self.audio.shutdown()
        print("[BRIDGE] Terminé.")

    def stop(self):
        self._stop.set()


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def _install_signal_handlers(bridge: DMXAudioBridge):
    def handler(signum, frame):
        print(f"[BRIDGE] Signal {signum} → arrêt")
        bridge.stop()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Chambre sonore — pont DMX+Audio (Orbbec Gemini 2)")
    p.add_argument("--sensor", choices=["gemini2"], default="gemini2")
    p.add_argument("--config", default="config/chambre_sonore_map.json")
    p.add_argument("--fps", type=int, default=15)
    p.add_argument("--depth-threshold", type=int, default=None)
    p.add_argument("--show-grid", action="store_true")
    p.add_argument("--dmx-verbose", action="store_true")
    a = p.parse_args(argv)
    cfg = BridgeConfig.load_or_create(a.config)
    if a.depth_threshold:
        cfg.depth_threshold_mm = a.depth_threshold
    bridge = DMXAudioBridge(cfg, a.fps, a.sensor, a.show_grid, a.dmx_verbose)
    _install_signal_handlers(bridge)
    bridge.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

