import crypt
import psycopg2

from fsmi.models import User

class AuthBackend(object):
    def authenticate(self, username, password):
        user = User.objects.get(username=username)
        if crypt.crypt(password, user.pw_hash) == user.pw_hash:
            return user
        else:
            return None

    def get_user(self, user_id):
        return User.objects.get(id=user_id)
