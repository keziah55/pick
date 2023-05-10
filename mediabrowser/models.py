from django.db import models

class MediaSeries(models.Model):
    title = models.CharField(max_length=200, primary_key=True, unique=True)
    def __str__(self):
        return self.title
    
class Person(models.Model):
    name = models.CharField(max_length=200, primary_key=True, unique=True)
    def __str__(self):
        return self.name
    
class Genre(models.Model):
    name = models.CharField(max_length=200, primary_key=True, unique=True)
    def __str__(self):
        return self.name
    
class Keyword(models.Model):
    name = models.CharField(max_length=200, primary_key=True, unique=True)
    def __str__(self):
        return self.name
    
class MediaItem(models.Model):
    # required
    title = models.CharField(max_length=500)
    filename = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField()
    img = models.CharField(max_length=500) # url to image
    runtime =  models.PositiveSmallIntegerField() # runtime in minutes
    imdb_id = models.PositiveIntegerField()
    
    # optional
    alt_title = models.CharField(max_length=1000, blank=True)
    language = models.CharField(max_length=1000, blank=True)
    colour = models.BooleanField(default=True)
    series = models.ForeignKey("MediaSeries", on_delete=models.CASCADE, blank=True, null=True)
    director = models.ManyToManyField(Person, related_name="director")
    stars = models.ManyToManyField(Person, related_name="stars")
    genre = models.ManyToManyField(Genre)
    keywords = models.ManyToManyField(Keyword)
    description = models.TextField()
    alt_versions = models.ManyToManyField('self', symmetrical=False)
    
    def __str__(self):
        return f"{self.title} ({int(self.year)})"