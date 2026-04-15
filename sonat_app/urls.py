from django.urls import path
from .views import api_login, api_register, api_data_user, api_edit_profile, api_logout, search_track, api_add_library, \
    api_get_library, api_filter_library, api_telegram_code_create, \
    api_status_connection_telegram, api_connecting_telegram, api_unconnected_telegram, api_upload_track, \
    api_delete_from_library

urlpatterns = [
    path('login/',api_login, name='api_login'),
    path('logout/', api_logout, name='api_logout'),
    path('register/', api_register, name='api_register'),
    path('profile/', api_data_user, name='api_data_user'),
    path('profile/edit/', api_edit_profile, name='api_edit_profile'),
    path('search/', search_track, name='api_search'),
    path('add_library/', api_add_library, name='api_add_library'),
    path("delete_track/", api_delete_from_library, name="api_delete_from_library"),
    path("library/", api_get_library, name="api_get_library"),
    path("filter/", api_filter_library, name="api_filter_library"),
    path("telegram_code/", api_telegram_code_create, name="api_telegram_code_create"),
    path("telegram/connected/", api_connecting_telegram, name="api_connected_telegram"),
    path("telegram/logout/", api_unconnected_telegram, name="api_connected_telegram"),
    path("telegram/status/", api_status_connection_telegram, name="api_status_connection_telegram"),
    path("telegram/upload_track/", api_upload_track, name="api_upload_track")
]