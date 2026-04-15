import datetime
import json
import secrets
import uuid

from django.contrib.auth import authenticate, login, logout
from django.core.files.uploadedfile import UploadedFile
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from sonat_app.models import User, UserProfile, Track, UserLibraryItem, TelegramConnection, TelegramUpload
from sonat_app.searchTrack import search_youtube, search_spotify


@csrf_exempt
def api_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return JsonResponse({"error": "Username and password required"}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    login(request, user)
    return JsonResponse({"success": True, "message": "Login successful"})

@csrf_exempt
def api_register(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    if not username or not password:
        return JsonResponse({"error": "Username and password required"}, status=400)

    if password != confirm_password:
        return JsonResponse({"error": "Passwords do not match"}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already exists"}, status=400)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )

    UserProfile.objects.create(
        user=user,
        first_name="",
        last_name="",
        description="",
        birth_day=None,
    )

    return JsonResponse({
        'success': True,
        'message': 'User created',
        'user_id': user.id,
    })

def api_data_user(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user = request.user

    return JsonResponse({
        "username": user.username,
        "first_name": user.profile.first_name,
        "last_name": user.profile.last_name,
        "description": user.profile.description,
        "birth_day": user.profile.birth_day.isoformat() if user.profile.birth_day else "",
    })

def api_edit_profile(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user = request.user

    username = data.get("username")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    birth_day = data.get("birth_day")
    description = data.get("description")

    if username is not None:
        user.username = username.strip()

    if first_name is not None:
        user.profile.first_name = first_name.strip()

    if last_name is not None:
        user.profile.last_name = last_name.strip()

    if description is not None:
        user.profile.description = description.strip()

    if birth_day is not None:
        try:
            user.profile.birth_day = datetime.datetime.strptime(birth_day, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

    user.profile.save()
    user.save()

    return JsonResponse({
        "message": "User data updated successfully",
    })

def api_logout(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    logout(request)
    return JsonResponse({"message": "Logged out successfully"})


def search_track(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    search_type = data.get("searchType")
    search_value = data.get("searchValue")

    if search_type == "youtube":
        tracks = search_youtube(search_value)
    else:
        tracks = search_spotify(search_value)

    return JsonResponse(tracks, safe=False)

def api_add_library(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user = request.user

    title = data.get("title")
    artist = data.get("author")
    cover_url = data.get("cover")
    external_url = data.get("watchUrl")
    source_type = data.get("sourceType")
    source_id = data.get("sourceId")

    track_is_exist = Track.objects.filter(source_id=source_id,source_type=source_type).exists()

    if track_is_exist is False:
        track = Track.objects.create(
            source_type=source_type,
            source_id=source_id,
            title=title,
            artist=artist,
            cover_url=cover_url,
            external_url=external_url,
        )
    else:
        track = Track.objects.filter(source_id=source_id, source_type=source_type).first()

    exist_in_library = UserLibraryItem.objects.filter(track_id=track.id, user_id=user.id).exists()

    if exist_in_library is False:
        UserLibraryItem.objects.create(
            track_id=track.id,
            user_id=user.id,
        )
    else:
        return JsonResponse({"message": "Track already in library"})

    return JsonResponse({"message": "Track successfully add to library"})

def api_delete_from_library(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user = request.user

    source_id = data.get("sourceId")
    source_type = data.get("sourceType")

    if not source_id or not source_type:
        return JsonResponse({"error": "source_id and source_type required"}, status=400)

    find_track = Track.objects.filter(source_id=source_id, source_type=source_type).first()
    UserLibraryItem.objects.filter(track_id=find_track.id, user_id = user.id).delete()

    return JsonResponse({"message": "Track successfully deleted"}, status=200)


def api_get_library(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user = request.user

    library_items = (
        UserLibraryItem.objects
        .filter(user_id=user.id)
        .select_related("track")
        .order_by("-id")
    )

    tracks = []

    for item in library_items:
        track = item.track

        tracks.append({
            "id": track.source_id if track.source_id else track.id,
            "title": track.title,
            "author": track.artist,
            "cover": track.cover_url,
            "watchUrl": track.external_url,
            "sourceId": track.source_id,
            "sourceType": track.source_type,
        })

    return JsonResponse({"tracks": tracks})

def api_filter_library(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user = request.user
    source_type = request.GET.get("sourceType")

    library_items = (
        UserLibraryItem.objects
        .filter(user_id=user.id)
        .select_related("track")
        .order_by("-id")
    )

    if source_type:
        library_items = library_items.filter(track__source_type=source_type)

    tracks = []

    for item in library_items:
        track = item.track

        tracks.append({
            "id": track.source_id if track.source_id else track.id,
            "title": track.title,
            "author": track.artist,
            "cover": track.cover_url,
            "watchUrl": track.external_url,
            "sourceId": track.source_id,
            "sourceType": track.source_type,
        })

    return JsonResponse({"tracks": tracks})


def api_telegram_code_create(request):
    def random_code():
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        code = ""

        for i in range(8):
            if i == 4:
                code += "-"
            code += secrets.choice(chars)

        return code

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    user = request.user

    telegram_connect = bool(user.telegram_id)

    if telegram_connect:
        return JsonResponse({"error":"Telegram already connected for this account"},status=400)

    TelegramConnection.objects.filter(
        user=user,
        valid=True,
    ).update(valid=False)

    code = random_code()

    TelegramConnection.objects.create(
        user=user,
        code=code,
    )

    return JsonResponse({"code": code},status=201)

@csrf_exempt
def api_connecting_telegram(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    code = data.get("code")
    telegram_id = data.get("telegram_id")

    find_code_in_table = TelegramConnection.objects.filter(
        code=code,
        valid=True,
        expired_to__gt=timezone.now(),
    ).first()

    if not find_code_in_table:
        return JsonResponse({"error":"This code not valid"})

    telegram_already_connected = User.objects.filter(id=find_code_in_table.user_id, telegram_id__isnull=False).exists()

    if telegram_already_connected:
        return JsonResponse({"error":"This account already connected to telegram"},status=400)

    User.objects.filter(id=find_code_in_table.user_id).update(telegram_id=telegram_id)

    TelegramConnection.objects.filter(user_id=find_code_in_table.user_id, code=code).update(valid=False)

    return JsonResponse({"success":"Successful connected"},status=200)

@csrf_exempt
def api_unconnected_telegram(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    telegram_id = data.get("telegram_id")

    unconnected = User.objects.filter(telegram_id=telegram_id).update(telegram_id=None)

    if not unconnected:
        return JsonResponse({"error":"Error unlinked account"}, status=400)

    return JsonResponse({"success":"Account successful unlinked"},status=200)

@csrf_exempt
def api_status_connection_telegram(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    telegram_id = data.get("telegram_id")

    if User.objects.filter(telegram_id=telegram_id):
        return JsonResponse({"connected": True}, status=200)

    return JsonResponse({"connected": False}, status=200)

@csrf_exempt
def api_upload_track(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    telegram_id = request.POST.get("telegram_id")
    title = request.POST.get("title")
    author = request.POST.get("author")

    cover = request.FILES.get("cover")
    audio = request.FILES.get("audio")

    if not telegram_id or not title or not author or not cover or not audio:
        return JsonResponse({"error": "Missing required fields"}, status=400)

    user = User.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return JsonResponse({"error": "Telegram account not linked"}, status=400)

    upload_track = TelegramUpload.objects.create(
        telegram_id=telegram_id,
        cover_file=cover,
        audio_file=audio
    )

    track_create = Track.objects.create(
        source_type="telegram",
        source_id=uuid.uuid4().hex,
        title=title,
        artist=author,
        cover_url=request.build_absolute_uri(upload_track.cover_file.url),
        external_url=request.build_absolute_uri(upload_track.audio_file.url)
    )

    UserLibraryItem.objects.create(
        added_at=timezone.now(),
        track_id=track_create.id,
        user_id=user.id
    )

    return JsonResponse({"ok": True}, status=200)




















