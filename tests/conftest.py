from django.contrib.auth import get_user_model

User = get_user_model()


def create_test_user():
    user = User.objects.create_user(
        username='testadmin',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
    )
    return user


def login_client(client, user=None):
    if user is None:
        user = User.objects.filter(username='testadmin').first()
        if user is None:
            user = create_test_user()
    client.login(username=user.username, password='testpass123')
    return user
