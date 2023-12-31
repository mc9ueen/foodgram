from re import match

from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.models import Follow, User

from .fields import Base64ImageField


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class OnlyRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'password')

    def validate_username(self, value):
        if not match(r'^[\w.@+-]+$', value):
            raise ValidationError(
                'Username содержит недопустимые символы'
            )
        return value


class CustomUserReadSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (request
                and request.user.is_authenticated
                and Follow.objects.filter(
                    user=request.user, author=obj
                ).exists()
                )


class PasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)


class FollowSerializer(serializers.ModelSerializer):
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    recipes = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        user = self.context['request'].user
        if not request or not user.is_authenticated:
            return False
        return obj.following.filter(user=user).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit_recipes = request.query_params.get('recipes_limit')
        if limit_recipes is not None:
            recipes = obj.recipes.all()[:(int(limit_recipes))]
        else:
            recipes = obj.recipes.all()
        context = {'request': request}
        return OnlyRecipeSerializer(recipes, many=True, context=context).data


class FollowToSerializer(serializers.Serializer):
    def validate(self, data):
        user = self.context.get('request').user
        author = get_object_or_404(User, pk=self.context['id'])
        if user == author:
            raise serializers.ValidationError(
                'Вы не можете подписаться на себя'
            )
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя'
            )
        return data

    def create(self, validated_data):
        user = self.context.get('request').user
        author = get_object_or_404(User, pk=validated_data['id'])
        Follow.objects.create(user=user, author=author)
        serializer = FollowSerializer(
            author, context={'request': self.context.get('request')}
        )
        return serializer.data


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurements_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError(
                'Количество ингредиента должно быть больше 0'
            )
        return value


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError(
                'Количество ингредиента должно быть больше 0'
            )
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        recipe_id = request.GET.get('recipe')
        ingredient_id = attrs['ingredient']['id']
        existing_ingredients = RecipeIngredient.objects.filter(
            recipe_id=recipe_id,
            ingredient_id=ingredient_id
        )
        if existing_ingredients.exists():
            raise ValidationError('Ингредиент уже добавлен в рецепт')
        return attrs


class RecipeReadSerializer(serializers.ModelSerializer):
    author = CustomUserReadSerializer(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    tags = TagSerializer(
        many=True,
        read_only=True
    )
    ingredients = RecipeIngredientReadSerializer(
        many=True, source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        user = request.user
        if not request or not user.is_authenticated:
            return False
        return obj.favorites.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        user = request.user
        if not request or not user.is_authenticated:
            return False
        shopping_cart = ShoppingCart.objects.filter(
            user=user, recipe=obj
        )
        return shopping_cart.exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all())
    ingredients = RecipeIngredientCreateSerializer(many=True)
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time',
        )

    def validate_cooking_time(self, value):
        if value <= 0:
            raise ValidationError(
                'Время приготовления должно быть больше 0'
            )
        return value

    def add_ingredients(self, recipe, ingredients_data):
        ingredients = []
        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data['ingredient']['id']
            amount = ingredient_data['amount']
            ingredient = Ingredient.objects.get(id=ingredient_id)
            if RecipeIngredient.objects.filter(
                    recipe=recipe, ingredient=ingredient_id).exists():
                amount += models.F('amount')
            recipe_ingredient = RecipeIngredient(
                recipe=recipe, ingredient=ingredient, amount=amount
            )
            ingredients.append(recipe_ingredient)
        RecipeIngredient.objects.bulk_create(ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.add_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', [])
        tags = validated_data.pop('tags')
        RecipeIngredient.objects.filter(recipe=instance).delete()
        self.add_ingredients(instance, ingredients)
        instance.tags.set(tags)
        return super().update(instance, validated_data)


class FavoriteSerializer(serializers.Serializer):
    def validate(self, data):
        recipe_id = self.context['recipe_id']
        user = self.context['request'].user
        if Favorite.objects.filter(
                user=user, recipe_id=recipe_id
        ).exists():
            raise serializers.ValidationError(
                'Этот рецепт уже есть в избранном'
            )
        return data

    def create(self, validated_data):
        recipe = get_object_or_404(Recipe, pk=validated_data['id'])
        user = self.context['request'].user
        Favorite.objects.create(user=user, recipe=recipe)
        serializer = OnlyRecipeSerializer(recipe)
        return serializer.data


class ShoppingCartSerializer(serializers.Serializer):
    def validate(self, data):
        recipe_id = self.context['recipe_id']
        user = self.context['request'].user
        if ShoppingCart.objects.filter(
                user=user, recipe_id=recipe_id
        ).exists():
            raise serializers.ValidationError(
                'Этот рецепт уже есть в списке покупок'
            )
        return data

    def create(self, validated_data):
        recipe = get_object_or_404(Recipe, pk=validated_data['id'])
        ShoppingCart.objects.create(
            user=self.context['request'].user,
            recipe=recipe
        )
        serializer = OnlyRecipeSerializer(recipe)
        return serializer.data
