import cv2


from motion_detector import detection

if __name__ == '__main__':
    cap = cv2.VideoCapture(0)
    detection(cap)
