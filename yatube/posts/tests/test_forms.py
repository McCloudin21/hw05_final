from posts.forms import PostForm
from ..models import Post, Group
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='Test')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def setUp(self):
        self.group = Group.objects.create(
            title='test-group',
            slug='first',
            description='test-description'
        )
        self.posts = Post.objects.create(
            text='Тестовый текст',
            group=self.group,
            author=self.user
        )

    def test_create_form(self):
        """Валидная форма создает запись в post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'test_text',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse('posts:profile',
                                               args=[self.posts.author]))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='test_text',
                group=self.group.id,
            ).exists()
        )

    def test_create_form_invalid_data(self):
        """Не валидная форма просит заполнить поле."""
        posts_count = Post.objects.count()
        form_data = {
            'text': ' ',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFormError(
            response,
            'form',
            'text',
            'Обязательное поле.',
        )
        self.assertEqual(response.status_code, 200)

    def test_create_post_guest_user(self):
        """Валидная форма не создаст запись в Post если неавторизован."""
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Изменяем текст',
            'group': self.group.id
        }
        response = self.guest_client.post(
            reverse('posts:post_edit', args=({self.post.id})),
            data=form_data,
        )
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/{self.post.id}/edit/'
                             )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(Post.objects.filter(text='Изменяем текст').exists())


class PostEditFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()
        cls.guest_client = Client()
        cls.user = User.objects.create_user(username='Test')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def setUp(self):
        self.group = Group.objects.create(
            title='test-group',
            slug='first',
            description='test-description'
        )
        self.posts = Post.objects.create(
            text='Тестовый текст',
            group=self.group,
            author=self.user
        )

    def test_edit_form(self):
        """Валидная форма редактирует запись в post."""
        form_data = {
            'text': 'test_text2',
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    args=[self.posts.id]
                    ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, reverse('posts:post_detail',
                                               args=[self.posts.id]))
        self.assertTrue(
            Post.objects.filter(
                text='test_text2',
            ).exists()
        )

    def test_post_edit_not_create_guest_client(self):
        """Валидная форма не изменит запись в Post если неавторизован."""
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
        )
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        posts_count = Post.objects.count()
        form_data = {'text': 'Изменяем текст', 'group': self.group.id}
        response = self.guest_client.post(
            reverse('posts:post_edit',
                    args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response,
                             f'/auth/login/?next=/posts/{self.post.id}/edit/'
                             )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(Post.objects.filter(text='Изменяем текст').exists())
