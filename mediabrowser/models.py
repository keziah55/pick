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
    MEDIA_TYPE_CHOICES = [
        ('FILM', 'film'),
        ('EPISODE', 'episode'),
        ('MUSIC_VIDEO', 'music_video'),
        ('VIDEO', 'video'),
        ('SONG', 'song')
    ]
    
    title = models.CharField(max_length=500)
    filename = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField()
    img = models.CharField(max_length=500) # url to image
    media_type = models.CharField(
        max_length=50,
        choices=MEDIA_TYPE_CHOICES)
    
    def __str__(self):
        return f"{self.title} ({int(self.year)})"
    
class VisionItem(MediaItem):
    runtime =  models.PositiveSmallIntegerField() # runtime in minutes
    alt_title = models.CharField(max_length=1000, blank=True)
    language = models.CharField(max_length=1000, blank=True)
    colour = models.BooleanField(default=True)
    series = models.ForeignKey("MediaSeries", on_delete=models.CASCADE, blank=True, null=True)
    director = models.ManyToManyField(Person, related_name="director", through="Member")
    stars = models.ManyToManyField(Person, related_name="stars", through="Member")
    genre = models.ManyToManyField(Genre)
    keywords = models.ManyToManyField(Keyword)
    description = models.TextField()
    alt_versions = models.ManyToManyField('self', symmetrical=False)
    
class SoundItem(MediaItem):
    pass
    
class Member(models.Model):
    # intermediary table to allow MediaItem to return e.g. stars in order they were added
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    mediaitem = models.ForeignKey(MediaItem, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True) 