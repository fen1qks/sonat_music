from contextlib import nullcontext
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone

def telegram_code_expires():
    return timezone.now() + timedelta(minutes=2)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    telegram_id = models.CharField(max_length=100, unique=True, blank=True, null=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    birth_day = models.DateField(null=True,blank=True)
    description = models.TextField(max_length=150, blank=True)

class Track(models.Model):
    class SourceType(models.TextChoices):
        SPOTIFY = 'spotify', 'Spotify'
        TELEGRAM = 'telegram', 'Telegram'
        YOUTUBE = 'youtube', 'Youtube'

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, blank=True, null=True)
    cover_url = models.URLField(blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)

    class Meta:
        unique_together = ('source_type', 'source_id')


class UserLibraryItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='library_items')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='library_items')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'track')

class TelegramUpload(models.Model):
    telegram_id = models.CharField(max_length=100,blank=True)
    audio_file = models.FileField(upload_to="audio_files/", blank=True, null=True)
    cover_file = models.FileField(upload_to="cover_files/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class TelegramConnection(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_connection')
    code = models.CharField(max_length=15,blank=True)
    expired_to = models.DateTimeField(default=telegram_code_expires)
    valid = models.BooleanField(default=True, blank=True)

    class Meta:
        unique_together = ('user', 'code')