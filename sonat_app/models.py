from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

class User(AbstractUser):
    email = models.EmailField(unique=True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    birth_day = models.DateField(null=True,blank=True)
    description = models.TextField(max_length=150, blank=True)

class UserConnection(models.Model):
    class Provider(models.TextChoices):
        SPOTIFY = 'spotify', 'Spotify'
        TELEGRAM = 'telegram', 'Telegram'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    external_user_id = models.CharField(max_length=255, blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'provider')

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
    duration = models.IntegerField(blank=True, null=True)
    metadate = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('source_type', 'source_id')


class UserLibraryItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='library_items')
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='library_items')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'track')

class UploadedMedia(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_file')
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)




