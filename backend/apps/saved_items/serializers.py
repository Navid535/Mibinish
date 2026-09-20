from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.saved_items import services
from apps.saved_items.models import Category, SavedItem, SavedItemCategory


class CategorySerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Category
        fields = ('id', 'user', 'name', 'color')
        validators = [
            UniqueTogetherValidator(
                queryset=Category.objects.all(),
                fields=('user', 'name'),
                message="You already have a category with this name.",
            )
        ]


class SavedItemCategorySerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    priority = serializers.IntegerField(min_value=1, default=1)

    class Meta:
        model = SavedItemCategory
        fields = ('category', 'priority')

    def validate_category(self, category):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or category.user_id != user.id:
            raise serializers.ValidationError("Invalid category.")
        return category


class SavedItemSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    categories = SavedItemCategorySerializer(source='category_links', many=True, required=False)

    class Meta:
        model = SavedItem
        fields = (
            'id', 'user', 'name', 'url', 'source',
            'extracted_content', 'metadata',
            'status', 'completed_at',
            'categories',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'extracted_content', 'metadata',
            'completed_at', 'created_at', 'updated_at',
        )

    def validate(self, attrs):
        name = attrs.get('name', getattr(self.instance, 'name', None))
        url = attrs.get('url', getattr(self.instance, 'url', None))
        if not name and not url:
            raise serializers.ValidationError("Either name or url must be provided.")

        category_links = attrs.get('category_links')
        if category_links is not None:
            category_ids = [link['category'].id for link in category_links]
            if len(category_ids) != len(set(category_ids)):
                raise serializers.ValidationError(
                    {"categories": "Duplicate categories are not allowed."}
                )
        return attrs

    def create(self, validated_data):
        category_links = validated_data.pop('category_links', [])
        user = validated_data.pop('user')
        return services.create_saved_item(
            user=user,
            category_links=category_links,
            **validated_data,
        )

    def update(self, instance, validated_data):
        validated_data.pop('user', None)
        category_links = validated_data.pop('category_links', None)
        return services.update_saved_item(
            saved_item=instance,
            category_links=category_links,
            **validated_data,
        )