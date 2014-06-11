import re

class DbRouter(object):
    @staticmethod
    def _get_db(model):
        if model.__module__ == 'fsmi.models':
            return 'fsmi'
        elif model.__module__ == 'prfproto.models':
            return 'prfproto'
        else:
            return 'default'

    def db_for_read(self, model, **hints):
        return self._get_db(model)

    def db_for_write(self, model, **hints):
        return self._get_db(model)

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_syncdb(self, db, model):
        return self._get_db(model) == 'odie'
