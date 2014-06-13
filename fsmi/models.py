from django.db import models

class User(models.Model):
    id = models.IntegerField(db_column='benutzer_id', primary_key=True)
    username = models.CharField(db_column='benutzername', unique=True, max_length=255, blank=True)
    first_name = models.TextField(db_column='vorname')
    last_name = models.TextField(db_column='nachname')
    pw_hash = models.CharField(db_column='passwort', max_length=255)
    unix_uid = models.IntegerField()

    def is_authenticated(self):
        return True

    def get_full_name(self):
        return self.first_name + ' ' + self.last_name

    def get_short_name(self):
        return self.username

    last_login = None
    def save(self, **kwargs):
        # ignore, used only for setting last_login
        pass

    REQUIRED_FIELDS = []  # not used, still necessary
    USERNAME_FIELD = 'username'
    class Meta:
        db_table = 'benutzer'
        managed = False
