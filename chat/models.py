from django.conf import settings
from django.db import models

from users.utils import fmt_dt


class Message(models.Model):
    """Eski Flask'dagi 'messages' jadvalining Django ekvivalenti."""
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sent_messages", on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="received_messages", on_delete=models.CASCADE)
    text = models.TextField(blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    attachment = models.FileField(upload_to="chat/", blank=True, null=True)
    attachment_type = models.CharField(max_length=20, blank=True, null=True)
    attachment_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["id"]

    def to_public(self):
        return {
            "id": self.id,
            "senderId": self.sender_id,
            "receiverId": self.receiver_id,
            "text": self.text,
            "isRead": self.is_read,
            "createdAt": fmt_dt(self.created_at),
            "attachment": self.attachment.url if self.attachment else None,
            "attachmentType": self.attachment_type,
            "attachmentName": self.attachment_name,
        }