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
    finally:
        # Ako je snimanje u toku, spasi video pre nego što se ugasi
        if snimač.recording:
            logging.warning(" Program prekidan! Spašavam nedovršeno snimanje...")
            video_path = snimač.save_video()
            if video_path:
                upload_video(video_path)

        snimač.release()
