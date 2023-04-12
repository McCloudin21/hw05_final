import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import (Client,
                         override_settings,
                         TestCase,
                         )
from django.urls import reverse

from posts.models import (Post,
                          Group,
                          Comment,
                          Follow,
                          )

POSTS_ON_PAGE: int = 13
POSTS_ON_FIRST_PAGE: int = 10
POSTS_ON_SECOND_PAGE: int = 3

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test_group')
        self.group2 = Group.objects.create(title='Тестовая группа 2',
                                           slug='test_group_2')
        self.post = Post.objects.create(
            author=self.user,
            text='Текст',
            group=self.group
        )

    def test_pages_uses_correct_template(self):
        """Страницы используют корректные шаблоны."""
        templates_pages_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/post_create.html',
        }
        for adress, template in templates_pages_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                error_name: str = f'Ошибка: {adress} ожидал шаблон {template}'
                self.assertTemplateUsed(response, template, error_name)

    def test_home_page_show_correct_context(self):
        """Страница index использует нужный контекст."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        page_object = response.context.get('page_obj')[0]
        self.assertEqual(page_object.author.username, 'StasBasov')
        self.assertEqual(page_object.text, 'Текст')
        self.assertEqual(page_object.group.title, 'Тестовая группа')

    def test_group_list_page_show_correct_context(self):
        """Страница group_list использует нужный контекст."""
        response = self.authorized_client.get(f'/group/{self.group.slug}/')
        expected_keys = [
            'group',
            'page_obj',
        ]
        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(key, response.context)
        page_object = response.context.get('page_obj')[0]
        self.assertEqual(page_object.author.username, 'StasBasov')
        self.assertEqual(page_object.text, 'Текст')
        self.assertEqual(page_object.group.title, 'Тестовая группа')

    def test_profile_page_show_correct_context(self):
        """Страница profile использует нужный контекст."""
        response = self.authorized_client.get(f'/profile/{self.user}/')
        expected_keys = [
            'author',
            'title',
            'posts_count',
            'page_obj',
        ]
        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(key, response.context)
        page_object = response.context.get('page_obj')[0]
        self.assertEqual(page_object.author.username, 'StasBasov')
        self.assertEqual(page_object.text, 'Текст')
        self.assertEqual(page_object.group.title, 'Тестовая группа')

    def test_post_detail_show_correct_context(self):
        """Страница post_detail использует нужный контекст."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        expected_keys = [
            'post',
            'posts_count',
        ]
        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(key, response.context)
        self.assertEqual(
            response.context.get('post').text, self.post.text
        )
        self.assertEqual(
            response.context.get('post').author, self.post.author
        )
        self.assertEqual(
            response.context.get('post').group, self.post.group
        )

    def test_create_edit_show_correct_context(self):
        """Страница post_edit использует нужный контекст."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        expected_keys = [
            'form',
            'is_form_edit',
            'post',
            'title',
        ]
        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(key, response.context)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Страница create использует нужный контекст."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        self.assertIn('form', response.context)
        self.assertIn('title', response.context)
        expected_keys = [
            'form',
            'title',
        ]
        for key in expected_keys:
            with self.subTest(key=key):
                self.assertIn(key, response.context)
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_shown_in_desired_group(self):
        """Пост записывается в нужную группу."""
        pages = [
            '/',
            f'/group/{self.group.id}/'
        ]
        for adress in pages:
            with self.subTest(adress=adress):
                self.assertTrue(
                    Post.objects.filter(text=self.post.text,
                                        group=self.group.id
                                        ).exists()
                )

    def test_post_not_shown_in_desired_group(self):
        """Пост не записывается в другую группу"""
        self.assertFalse(
            Post.objects.filter(text=self.post.text,
                                group=self.group2.id
                                ).exists()
        )

    def test_comment_correct_context(self):
        """Валидная форма Комментария создает запись в Post."""
        comments_count = Comment.objects.count()
        form_data = {"text": "Тестовый коммент"}
        response = self.authorized_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse("posts:post_detail",
                              kwargs={"post_id": self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(
            text="Тестовый коммент"
        ).exists()
        )

    def test_check_cache(self):
        """Проверка кеша."""
        response = self.guest_client.get(reverse("posts:index"))
        Post.objects.get(id=1).delete()
        response2 = self.guest_client.get(reverse("posts:index"))
        self.assertEqual(response.content, response2.content)

    def test_follow_page_clear(self):
        """Проверяем, что страница подписок пуста."""
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 0)

    def test_follow_on_author(self):
        """ Проверка подписки на автора поста."""
        Follow.objects.get_or_create(user=self.user, author=self.post.author)
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 1)

    def test_follow_on_subscriber(self):
        """проверка подписки у юзера-фоловера."""
        response = self.guest_client.get(reverse("posts:index"))
        self.assertIn(self.post, response.context["page_obj"])

    def test_not_show_on_not_subscriber(self):
        """Проверка что пост не появился в избранных у юзера-обычного."""
        outsider = User.objects.create(username="NoName")
        self.authorized_client.force_login(outsider)
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertNotIn(self.post, response.context["page_obj"])

    def test_unfollow(self):
        """Проверка отписки от автора поста."""
        Follow.objects.all().delete()
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 0)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(TaskPagesTests, cls).setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Test group',
            slug='test_group_slug',
            description='Test group description',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()

    def test_image_in_group_list_page(self):
        """Картинка передается на страницу group_list."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        )
        obj = response.context['page_obj'][0]
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_index_and_profile_page(self):
        """Картинка передается на страницу index_and_profile."""
        templates = (
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.post.author}),
        )
        for url in templates:
            with self.subTest(url):
                response = self.guest_client.get(url)
                obj = response.context['page_obj'][0]
                self.assertEqual(obj.image, self.post.image)

    def test_image_in_post_detail_page(self):
        """Картинка передается на страницу post_detail."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        obj = response.context['post']
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_page(self):
        """Проверяем что пост с картинкой создается в БД"""
        self.assertTrue(
            Post.objects.filter(text='Тестовый текст',
                                image='posts/small.gif'
                                ).exists()
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUp(self):
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test_group')
        bilk_post: list = []
        for i in range(POSTS_ON_PAGE):
            bilk_post.append(Post(text=f'Тестовый текст {i}',
                                  group=self.group,
                                  author=self.user))
        Post.objects.bulk_create(bilk_post)

    def test_first_page_contains_ten_records(self):
        """Первая страница показывает нужное количество постов."""
        pages = {
            '/': POSTS_ON_FIRST_PAGE,
            f'/group/{self.group.slug}/': POSTS_ON_FIRST_PAGE,
            f'/profile/{self.user}/': POSTS_ON_FIRST_PAGE,
        }
        for adress, expected_value in pages.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertEqual(len(response.context['page_obj']),
                                 expected_value)

    def test_second_page_contains_three_records(self):
        """Вторая страница показывает нужное количество постов."""
        pages = {
            '/': POSTS_ON_SECOND_PAGE,
            f'/group/{self.group.slug}/': POSTS_ON_SECOND_PAGE,
            f'/profile/{self.user}/': POSTS_ON_SECOND_PAGE,
        }
        for adress, expected_value in pages.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(str(adress) + '?page=2')
                self.assertEqual(len(response.context['page_obj']),
                                 expected_value)
