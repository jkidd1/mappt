from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from uploader import views as uploader_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', uploader_views.UploadView.as_view(), name='fileupload'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)