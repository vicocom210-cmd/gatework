from django.urls import path
from .views import ChatMessagesView, ChatSendView, ChatUnreadView, ChatThreadsView

urlpatterns = [
    path("messages", ChatMessagesView.as_view()),
    path("send", ChatSendView.as_view()),
    path("unread", ChatUnreadView.as_view()),
    path("threads", ChatThreadsView.as_view()),
]