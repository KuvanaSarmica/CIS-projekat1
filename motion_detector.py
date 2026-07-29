import cv2
from blob_service import save_snapshot
from queue_service import send_motion_events
import datetime as dt
url = "http://192.168.1.14:4747/video"

cap = cv2.VideoCapture()
ret,frame1 = cap.read()
ret,frame2 = cap.read()




poslednje_slanje=None
while cap.isOpened():

    diff = cv2.absdiff(frame1, frame2)

    gray2 = cv2.cvtColor(diff,cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray2,(5,5),0)
    _,thresh = cv2.threshold(blur,20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh,None,iterations=3)
    contours, _ = cv2.findContours(dilated,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

    mvm = False



    for contour in contours:
        if cv2.contourArea(contour)<700:
            continue
        mvm = True



        (cx, cy, cw, ch) = cv2.boundingRect(contour)
        cv2.putText(frame1,f"Detektovan pokret!",(10,20),cv2.FONT_HERSHEY_SIMPLEX,
                    1,(0,0,255),3)
    if mvm:
        if poslednje_slanje == None or (dt.datetime.now() - poslednje_slanje).total_seconds()>10:
            save_snapshot(frame1)
            send_motion_events()
            poslednje_slanje = dt.datetime.now()
    cv2.imshow('prozor',frame1)

    frame1=frame2
    ret,frame2 = cap.read()
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()





