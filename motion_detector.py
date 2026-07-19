import numpy as np
import cv2
from mypy.typeops import false_only
url = "http://192.168.1.14:4747/video"

cap = cv2.VideoCapture(url)
ret,frame1 = cap.read()
ret,frame2 = cap.read()
face_detected = False

face_cascade = cv2.CascadeClassifier(
    "haarcascade_frontalface_default.xml"
)

eye_cascade = cv2.CascadeClassifier(
    "haarcascade_eye.xml"
)


while cap.isOpened():

    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 2)
    for (x, y, w, h) in faces:
        face_detected = True
        diff[y:y + h + 20, x:x + w + 20] = 0
        cv2.putText(frame1, f"Detektovano lice!", (400, 20), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 3)

    gray2 = cv2.cvtColor(diff,cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray2,(5,5),0)
    _,thresh = cv2.threshold(blur,20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh,None,iterations=3)
    contours, _ = cv2.findContours(dilated,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

    mvm = False

    for contour in contours:
        (x,y,w,h) = cv2.boundingRect(contour)

        if cv2.contourArea(contour)<700:
            continue
        mvm = True
        (cx, cy, cw, ch) = cv2.boundingRect(contour)
        cv2.putText(frame1,f"Detektovan pokret!",(10,20),cv2.FONT_HERSHEY_SIMPLEX,
                    1,(0,0,255),3)



    for (x, y, w, h) in faces:
        cv2.rectangle(frame1, (x, y), (x + w, y + h), (255, 0, 0), 2)

    cv2.imshow('prozor',frame1)

    frame1=frame2
    ret,frame2 = cap.read()
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()





