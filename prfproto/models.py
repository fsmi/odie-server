from __future__ import unicode_literals

import os

from django.db import models
from django.utils import timezone
from odie import settings

class AccountingLog(models.Model):
    by_uid = models.IntegerField(db_column='benutzer')
    amount = models.DecimalField(db_column='betrag', max_digits=10, decimal_places=2)
    description = models.TextField(db_column='beschreibung', blank=True)
    time = models.DateTimeField(db_column='datumzeit', blank=True, null=True, default=timezone.now)
    account_id = models.IntegerField(db_column='abrechnungskonto', blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'abrechnung'

class Exam(object):
    @property
    def price(self):
        return settings.PRICE_PER_PAGE * self.page_count

    @property
    def file_path(self):
        raise NotImplementedError()

    @staticmethod
    def get(unified_id):
        if unified_id % 2 == 0:
            return WrittenExam.objects.get(id=unified_id // 2)
        else:
            return OralExam.objects.get(id=unified_id // 2)

#class Documents(models.Model):
#    id = models.BigIntegerField(blank=True, null=True)
#    date = models.DateField(blank=True, null=True)
#    examinants = models.TextField(blank=True) # This field type is a guess.
#    lectures = models.TextField(blank=True) # This field type is a guess.
#    comment = models.TextField(blank=True)
#    pages = models.BigIntegerField(blank=True, null=True)
#    examtype = models.TextField(db_column='examType', blank=True) # Field name made lowercase.
#    class Meta:
#        managed = False
#        db_table = 'documents'
#
#class Fehlkopien(models.Model):
#    id = models.IntegerField(primary_key=True)
#    vonaccount = models.IntegerField()
#    nachaccount = models.IntegerField()
#    seiten = models.IntegerField()
#    datum = models.DateTimeField(blank=True, null=True)
#    uebertragen = models.NullBooleanField()
#    class Meta:
#        managed = False
#        db_table = 'fehlkopien'
#
#class Gebiet(models.Model):
#    id = models.BigIntegerField(primary_key=True)
#    vertiefungsgebiet = models.TextField()
#    class Meta:
#        managed = False
#        db_table = 'gebiet'
#
class WrittenExam(models.Model, Exam):
#    vorlesung = models.TextField(blank=True)
#    prof = models.TextField(blank=True)
#    datum = models.DateField(blank=True, null=True)
#    kommentar = models.TextField(blank=True)
#    bestand = models.IntegerField(blank=True, null=True)
#    sollbestand = models.IntegerField(blank=True, null=True)
#    gueltigbis = models.DateField(blank=True, null=True)
    page_count = models.IntegerField(db_column='seiten', blank=True, null=True)
#    verkauft = models.BigIntegerField(blank=True, null=True)
#    veraltet = models.NullBooleanField()

    @property
    def file_path(self):
        return os.path.join(settings.ORAL_EXAMS_PATH, str(self.id) + '.pdf')

    class Meta:
        managed = False
        db_table = 'klausuren'

#class Klausurenlog(models.Model):
#    value = models.IntegerField()
#    klausur = models.BigIntegerField()
#    datum = models.DateTimeField()
#    class Meta:
#        managed = False
#        db_table = 'klausurenlog'
#
#class Ordner(models.Model):
#    id = models.BigIntegerField(primary_key=True)
#    name = models.TextField(blank=True)
#    verleihbar = models.BooleanField()
#    ausleihername = models.TextField(blank=True)
#    ausleihertelefon = models.TextField(blank=True)
#    ausleiheremail = models.TextField(blank=True)
#    verliehen = models.BooleanField()
#    verleihdatum = models.DateField(blank=True, null=True)
#    ordnerpfand = models.IntegerField()
#    protokollpfand = models.IntegerField()
#    class Meta:
#        managed = False
#        db_table = 'ordner'
#
class OralExam(models.Model, Exam):
#    gebiet = models.ForeignKey(Gebiet, db_column='gebiet')
#    datum = models.DateField()
    page_count = models.BigIntegerField(db_column='seiten')
#    ausgedruckt_fuer_ordner = models.BooleanField()

    @property
    def file_path(self):
        return os.path.join(settings.ORAL_EXAMS_PATH, str(self.id) + '.pdf')

    class Meta:
        managed = False
        db_table = 'protokolle'

class ProtocolDeposit(models.Model):
    student_name = models.TextField(db_column='name')
    #ordner1 = models.ForeignKey(Ordner, db_column='ordner1', blank=True, null=True)
    #ordner2 = models.ForeignKey(Ordner, db_column='ordner2', blank=True, null=True)
    #ordner3 = models.ForeignKey(Ordner, db_column='ordner3', blank=True, null=True)
    amount = models.BigIntegerField(db_column='betrag', blank=True, null=True)
    date = models.DateTimeField(db_column='datum', blank=True, null=True, default=timezone.now)
    by_user = models.TextField(db_column='benutzer', blank=True)
    class Meta:
        managed = False
        db_table = 'protokollpfand'

#class ProtokollpfandLog(models.Model):
#    log_id = models.IntegerField()
#    time = models.DateTimeField(blank=True, null=True)
#    wert = models.IntegerField(blank=True, null=True)
#    class Meta:
#        managed = False
#        db_table = 'protokollpfand_log'
#
#class Pruefer(models.Model):
#    id = models.BigIntegerField()
#    pruefername = models.TextField()
#    class Meta:
#        managed = False
#        db_table = 'pruefer'
#
#class Pruefungpruefer(models.Model):
#    protokollid = models.ForeignKey(Protokolle, db_column='protokollid')
#    prueferid = models.ForeignKey(Pruefer, db_column='prueferid')
#    class Meta:
#        managed = False
#        db_table = 'pruefungpruefer'
#
#class Pruefungvorlesung(models.Model):
#    protokollid = models.ForeignKey(Protokolle, db_column='protokollid')
#    vorlesungsid = models.ForeignKey('Vorlesungen', db_column='vorlesungsid')
#    dozent = models.TextField(blank=True)
#    id = models.BigIntegerField()
#    class Meta:
#        managed = False
#        db_table = 'pruefungvorlesung'
#
#class Vorbestellung(models.Model):
#    id = models.BigIntegerField()
#    protokollid = models.ForeignKey(Protokolle, db_column='protokollid')
#    datum = models.DateField()
#    class Meta:
#        managed = False
#        db_table = 'vorbestellung'
#
#class Vorlesungen(models.Model):
#    id = models.BigIntegerField(primary_key=True)
#    vorlesung = models.TextField()
#    class Meta:
#        managed = False
#        db_table = 'vorlesungen'
