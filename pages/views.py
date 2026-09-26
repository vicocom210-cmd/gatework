from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login


def index(request):
    return render(request, "index.html", {"page": "home"})


def about(request):
    return render(request, "about.html", {"page": "about"})


def rating(request):
    return render(request, "rating.html", {"page": "rating"})


def login_page(request):
    return render(request, "login.html", {"page": "login"})


def admin_page(request):
    """
    Eski Flask'dagi admin_page() ning ekvivalenti.

    MUHIM: bizda alohida "is_admin" maydoni yo'q — Django'ning
    tayyor "is_staff" maydonidan xuddi shu maqsadda foydalanamiz
    (superuser yaratganda bu avtomatik True bo'ladi).

    Endi bu sahifa saytning email-login formasiga emas, balki
    to'g'ridan-to'g'ri ODDIY username+parol shakliga (Django'ning
    o'zi ishlatadigan usul) tayanadi — pastdagi admin_login'ga.
    """
    if not request.user.is_authenticated:
        return redirect("admin-login")
    if not request.user.is_staff:
        return redirect("index")
    return render(request, "admin.html", {"page": "admin"})


def admin_login(request):
    """
    Django'ning o'zi ishlatadigan usul: username + parol. Muvaffaqiyatli
    kirilsa (va is_staff=True bo'lsa) — to'g'ridan-to'g'ri /admin/ga
    yo'naltiradi.
    """
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            auth_login(request, user)
            return redirect("admin-panel")
        error = "Username yoki parol noto'g'ri, yoki admin huquqi yo'q."
    return render(request, "admin_login.html", {"error": error})


def profile_page(request):
    if not request.user.is_authenticated:
        return redirect("/login/?redirect=/profile/")
    return render(request, "profile.html", {"page": "profile"})


def archive_page(request):
    if not request.user.is_authenticated:
        return redirect("/login/?redirect=/archive/")
    return render(request, "archive.html", {"page": "archive"})