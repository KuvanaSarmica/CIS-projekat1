import cv2
import time
import datetime as dt
import collections
import threading
import logging


class StreamCapture:

    def __init__(self):
        self.fps = 30
        self.width = 640
        self.height = 480

        # poslednje 3 sekunde
        self.buffer = collections.deque(
            maxlen=self.fps * 3
        )

        self.frames = []

        self.recording = False
        self.last_motion_time = 0

        self.stop_delay = 5  # koliko sekundi posle zadnjeg pokreta snima

        self.lock = threading.Lock()


    def add_frame(self, frame):

        frame = cv2.resize(
            frame,
            (self.width, self.height)
        )

        with self.lock:

            self.buffer.append(
                frame.copy()
            )

            if self.recording:
                self.frames.append(
                    frame.copy()
                )


    def motion(self):

        """
        Pozvati kada detektujemo pokret
        """

        with self.lock:

            # prvi pokret
            if not self.recording:

                self.frames = list(self.buffer)

                self.recording = True

                logging.info(
                    "Snimanje pokrenuto"
                )


            # svaki novi pokret samo produžava
            self.last_motion_time = time.time()



    def should_save(self):

        with self.lock:
            if not self.recording:
                return False

            if time.time() - self.last_motion_time > self.stop_delay:
                self.recording = False
                return True

            return False



    def save_video(self):

        with self.lock:

            frames = list(self.frames)

            self.frames.clear()


        if not frames:
            return None


        filename = (
            "/tmp/motion_" +
            dt.datetime.now().strftime(
                "%Y-%m-%d_%H-%M-%S"
            )
            +
            ".mp4"
        )


        writer = cv2.VideoWriter(
            filename,
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            (self.width,self.height)
        )


        for frame in frames:
            writer.write(frame)


        writer.release()


        logging.info(
            f"Video sacuvan {filename}"
        )


        return filename

    def release(self):
        with self.lock:
            self.buffer.clear()
            self.frames.clear()

        self.recording = False