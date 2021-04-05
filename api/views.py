from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .filters import TitleFilter
from .models import Category, Comment, CustomUser, Genre, Review, Title
from .permissions import (IsAdminOnly, IsAdminOrReadOnly,
                          ReviewCommentPermissions)
from .serializers import (CategorySerializer, CodeGenerationSerializer,
                          CommentSerializer, EmailConfirmationSerializer,
                          GenreSerializer, ReviewSerializer,
                          TitleWriteSerializer, UserSerializer,
                          TitleReadSerializer,
                          )
from api_yamdb.settings import EMAIL_HOST_USER as admin_email


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def generate_code(request):
    serializer = CodeGenerationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data.get('email')
    user = CustomUser.objects.get_or_create(email=email)[0]
    confirmation_code = default_token_generator.make_token(user)
    send_mail(
        'Confirmation code',
        f'Confirmation code: {confirmation_code}',
        admin_email,
        [f'{email}'],
    )
    success_text = f'Confirmation code was sent to {email}'
    return Response(success_text, status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def generate_token(request):
    serializer = EmailConfirmationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data.get('email')
    user = get_object_or_404(CustomUser, email=email)
    confirmation_code = serializer.validated_data.get('confirmation_code')
    if not default_token_generator.check_token(user, confirmation_code):
        fail_text = f'Point correct confirmation code for {email}'
        return Response(fail_text, status=status.HTTP_400_BAD_REQUEST)
    refresh = RefreshToken.for_user(user)
    token = str(refresh.access_token)
    return Response({'token': token}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated, IsAdminOnly)
    serializer_class = UserSerializer
    queryset = CustomUser.objects.all()
    search_fields = ['username', ]
    lookup_field = 'username'

    @action(detail=False, methods=['GET', 'PATCH'],
            permission_classes=(permissions.IsAuthenticated,))
    def me(self, request):
        user = self.request.user
        serializer = self.get_serializer(
            user, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class TitleViewSet(viewsets.ModelViewSet):
    queryset = Title.objects.all().annotate(rating=Avg('reviews__score'))
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TitleFilter
    permission_classes = (IsAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method.lower() == 'get':
            return TitleReadSerializer
        else:
            return TitleWriteSerializer


class CreateListDestroyViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
        viewsets.GenericViewSet):
    pass


class CategoryViewSet(CreateListDestroyViewSet):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', ]
    lookup_field = 'slug'


class GenreViewSet(CreateListDestroyViewSet):

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'slug']
    lookup_field = 'slug'


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [ReviewCommentPermissions, IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        title = get_object_or_404(Title, pk=self.kwargs.get('title_id'))
        return title.reviews.all()

    def perform_create(self, serializer):
        title = get_object_or_404(Title, pk=self.kwargs.get('title_id'))
        serializer.save(author=self.request.user, title=title)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [ReviewCommentPermissions, IsAuthenticatedOrReadOnly]

    def get_queryset(self, **kwargs):
        review = get_object_or_404(Review, pk=self.kwargs.get('review_id'))
        return Comment.objects.filter(review=review)

    def perform_create(self, serializer, **kwargs):
        review = get_object_or_404(Review, pk=self.kwargs.get('review_id'))
        serializer.save(author=self.request.user, review=review)
