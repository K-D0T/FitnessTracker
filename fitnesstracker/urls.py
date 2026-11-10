from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    # Login / logout / password-change views for the single-user setup.
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('home.urls')),
]

# Static files are served automatically by django.contrib.staticfiles when
# DEBUG is on, and by the web server (from STATIC_ROOT) in production, so
# there is deliberately no static()/serve() route here. The previous version
# called static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) with
# both settings undefined, which Django defaulted to '/' and '', producing a
# catch-all route that served the whole project directory -- including
# db.sqlite3 and settings.py -- over HTTP.
