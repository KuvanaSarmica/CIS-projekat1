from plyer import notification

def send_face_detection_notification(camera="main", timestamp=None):
    message = f"Face detected on camera {camera}."
    if timestamp is not None:
        message = f"{message} Time: {timestamp}"

    notification.notify(
        title="Face detected",
        message=message,
        app_name="Security Camera",
        timeout=5
    )
