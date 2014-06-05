from django.db import models

class Cart(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField('creation date')

    @property
    def document_ids(self):
        return [cartdocument.document_id for cartdocument in self.cartdocument_set.all()]

class CartDocument(models.Model):
    cart = models.ForeignKey(Cart)
    # cannot be a relation since it's cross-db _and_ id-transformed
    document_id = models.IntegerField()

class FsmiUser(models.Model):
    REQUIRED_FIELDS = []  # irrelevant but necessary field

    class Meta:
        managed = True  # don't create in db

    # ignore ignore ignore
    def save(self, *params, **kwargs):
        pass
