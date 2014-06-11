from __future__ import unicode_literals

from django.db import models

#class Abrechnung(models.Model):
#    id = models.IntegerField(primary_key=True)
#    benutzer = models.IntegerField()
#    betrag = models.DecimalField(max_digits=10, decimal_places=2)
#    beschreibung = models.TextField(blank=True)
#    datumzeit = models.DateTimeField(blank=True, null=True)
#    abrechnungskonto = models.IntegerField(blank=True, null=True)
#    class Meta:
#        managed = False
#        db_table = 'abrechnung'
#
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
#class Klausuren(models.Model):
#    id = models.BigIntegerField(primary_key=True)
#    vorlesung = models.TextField(blank=True)
#    prof = models.TextField(blank=True)
#    datum = models.DateField(blank=True, null=True)
#    kommentar = models.TextField(blank=True)
#    bestand = models.IntegerField(blank=True, null=True)
#    sollbestand = models.IntegerField(blank=True, null=True)
#    gueltigbis = models.DateField(blank=True, null=True)
#    seiten = models.IntegerField(blank=True, null=True)
#    verkauft = models.BigIntegerField(blank=True, null=True)
#    veraltet = models.NullBooleanField()
#    class Meta:
#        managed = False
#        db_table = 'klausuren'
#
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
#class Protokolle(models.Model):
#    id = models.BigIntegerField(primary_key=True)
#    gebiet = models.ForeignKey(Gebiet, db_column='gebiet')
#    datum = models.DateField()
#    seiten = models.BigIntegerField()
#    ausgedruckt_fuer_ordner = models.BooleanField()
#    class Meta:
#        managed = False
#        db_table = 'protokolle'
#
#class Protokollpfand(models.Model):
#    id = models.BigIntegerField(primary_key=True)
#    name = models.TextField()
#    ordner1 = models.ForeignKey(Ordner, db_column='ordner1', blank=True, null=True)
#    ordner2 = models.ForeignKey(Ordner, db_column='ordner2', blank=True, null=True)
#    ordner3 = models.ForeignKey(Ordner, db_column='ordner3', blank=True, null=True)
#    betrag = models.BigIntegerField(blank=True, null=True)
#    datum = models.DateTimeField(blank=True, null=True)
#    benutzer = models.TextField(blank=True)
#    class Meta:
#        managed = False
#        db_table = 'protokollpfand'
#
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
