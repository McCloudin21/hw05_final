from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import (Client,
                         TestCase
                         )

from ..models import (Group,
                      Post,
                      )


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='Test-User')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='test-group',
            slug='test-slug',
            description='test-description'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Test-User2')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_2 = User.objects.create_user(username='Test-User3')
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user_2)
        self.group = Group.objects.create(
            title='test-group-2',
            slug='test-slug-2',
            description='test-description'
        )
        self.post = Post.objects.create(
            text='Тестовый текст',
            author=self.user
        )

    def test_homepage(self):
        """Тестирование статуса страниц"""
        pages = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user}/',
            f'/posts/{self.post.id}/',
        ]
        for adress in pages:
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                error_name: str = f'Ошибка: нет доступа до страницы {adress}'
                self.assertEqual(response.status_code,
                                 HTTPStatus.OK,
                                 error_name
                                 )

    def test_unexisting_page(self):
        """Тестирование несуществующей страницы"""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_create_page(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/', follow=True,)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_page_redirect_guest_user(self):
        """Страница /create/ перенаправляет анонимного пользователя."""
        response = self.guest_client.get('/create/')
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_edit_page_redirect_not_author_of_post(self):
        """Страница /edit/ перенаправляет не автора поста."""
        response = self.authorized_client_2.get(f'/posts/{self.post.id}/edit/')
        self.assertRedirects(
            response, f'/posts/{self.post.id}/'
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/profile/{self.user}/': 'posts/profile.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                error_name: str = f'Ошибка: {adress} ожидал шаблон {template}'
                self.assertTemplateUsed(response, template, error_name)

    def test_post_edit_page_authorized_uses_correct_template(self):
        """URL-адрес post/<post_id>/edit использует соответствующий шаблон"""
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/',
        )
        self.assertTemplateUsed(response, 'posts/post_create.html')

    def test_post_create_page_authorized_uses_correct_template(self):
        """URL-адрес post/create/ использует соответствующий шаблон."""
        response = self.authorized_client.get('/create/'
                                              )
        self.assertTemplateUsed(response, 'posts/post_create.html')
