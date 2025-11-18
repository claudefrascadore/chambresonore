# Auto-généré par Codex le 2025-11-09 15:39
from pyorbbecsdk import Pipeline, OBSensorType
import cv2, numpy as np

print("Test de capture Orbbec Gemini 2…")
pipeline = Pipeline()
pipeline.start()
for i in range(100):
    frameset = pipeline.wait_for_frames(100)
    if not frameset:
        continue
    frame = frameset.get_depth_frame()
    if frame:
        data = np.frombuffer(frame.get_data(), dtype=np.uint16)
        img = cv2.convertScaleAbs(data.reshape(frame.get_height(), frame.get_width()), alpha=0.03)
        cv2.imshow("Depth", img)
        if cv2.waitKey(1) & 0xFF == 27:
            break
pipeline.stop()
cv2.destroyAllWindows()
print("✅ Test terminé.")

