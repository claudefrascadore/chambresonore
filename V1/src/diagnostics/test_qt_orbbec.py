import sys
from PyQt6.QtWidgets import QApplication
import pyorbbecsdk as ob

def main():
    print(">>> Lancement test Qt + Pipeline…")

    app = QApplication(sys.argv)

    print(">>> Création pipeline Orbbec…")
    pipe = ob.Pipeline()
    print(">>> Pipeline créé.")

    print(">>> Lecture profils profondeur…")
    profiles = pipe.get_stream_profile_list(ob.OBSensorType.DEPTH_SENSOR)
    print(">>> OK, profils :", profiles)

    print(">>> Fin.")
    sys.exit(0)

if __name__ == "__main__":
    main()

