# push_notification.py
from plyer import notification


def send_face_detection_notification(camera="main", timestamp=None, tags=None, objects=None):
    message = f"Face detected on camera '{camera}'."

    if timestamp:
        message += f"\nTime: {timestamp}"

    if tags:
        # Show top 5 tags
        message += f"\nTags: {', '.join(tags[:5])}"

    if objects:
        message += f"\nObjects: {', '.join(objects)}"

    notification.notify(
        title="Security Alert: Face Detected",
        message=message,
        app_name="Security Camera",
        timeout=8
    )