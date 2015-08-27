from odie import sqla, Column

class Location(sqla.Model):
    __tablename__ = 'locations'
    __table_args__ = {
        'schema': 'garfield',
        'info': {'bind_key': 'garfield'}
    }

    id = Column(sqla.Integer, name='location_id', primary_key=True)
    name = Column(sqla.String, name='location_name')
    description = Column(sqla.String, name='location_description')

    def __str__(self):
        return self.name

    def to_subject(self):
        return 'computer science' if self.name == 'FSI' else 'mathematics'
