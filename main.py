import cv2
from stream_capture import StreamCapture
from blob_service import upload_video
from motion_detector import detection
import logging

if __name__ == '__main__':
    url = 'http://192.168.1.18:4747/video'
    cap = cv2.VideoCapture(0)
    snimač = StreamCapture()

    try:
        detection(cap, snimač)  # Prosleđi snimač kao parametar
    except KeyboardInterrupt:
        print("\n[Info] Program zaustavljen od strane korisnika (KeyboardInterrupt).")
    finally:
        # Ako je snimanje u toku, spasi video pre nego što se ugasi
        if snimač.recording:
            print("WARNING: Program prekidan! Spašavam nedovršeno snimanje...")
            video_path = snimač.save_video()
            if video_path:
                print(f"[Info] Pokušavam upload poslednjeg videa: {video_path}")
                try:
                    upload_video(video_path)
                except KeyboardInterrupt:
                    print("\n[Warning] Upload prekinut ponovnim KeyboardInterrupt-om. Lokalni fajl će biti obrisan.")

        snimač.release()
