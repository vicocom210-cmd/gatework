from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """
    DRF xatolarini frontend kutadigan ko'rinishga keltiradi:
    {"detail": "..."} → {"ok": false, "error": "...", "detail": "..."}
    (auth.js, chat.js, profile.js xabarni data.error'dan oladi).
    """
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and "detail" in response.data:
        response.data = {"ok": False, "error": str(response.data["detail"]), "detail": response.data["detail"]}
    return response
