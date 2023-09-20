from django.urls import include, path
from rest_framework.routers import DefaultRouter


from api.views import IngredientViewSet, RecipeViewSet, TagViewSet, UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'tags', TagViewSet, basename='tags')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')

urlpatterns = (
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),
)
