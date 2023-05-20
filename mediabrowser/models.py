from django.db import models
from sortedm2m.fields import SortedManyToManyField

class MediaSeries(models.Model):
    title = models.CharField(max_length=200, primary_key=True, unique=True)
    def __str__(self):
        return self.title
    
class Person(models.Model):
    name = models.CharField(max_length=200, primary_key=True, unique=True)
    # TODO aka, e.g. Charlie Chaplin?
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
    
# class MediaItem(models.Model):
#     FILM = 'FILM'
#     EPISODE = 'EPISODE'
#     MUSIC_VIDEO ='MUSIC_VIDEO'
#     VIDEO = 'VIDEO'
#     SONG = 'SONG'
    
#     MEDIA_TYPE_CHOICES = [
#         (FILM, 'film'),
#         (EPISODE, 'episode'),
#         (MUSIC_VIDEO, 'music_video'),
#         (VIDEO, 'video'),
#         (SONG, 'song')
#     ]
    
#     title = models.CharField(max_length=500)
#     filename = models.CharField(max_length=200)
#     year = models.PositiveSmallIntegerField()
#     img = models.CharField(max_length=500) # url to image
#     media_type = models.CharField(
#         max_length=50,
#         choices=MEDIA_TYPE_CHOICES)
    
#     def __str__(self):
#         return f"{self.title} ({int(self.year)})"
    
class VisionItem(models.Model):
    FILM = 'FILM'
    EPISODE = 'EPISODE'
    MUSIC_VIDEO ='MUSIC_VIDEO'
    VIDEO = 'VIDEO'
    
    MEDIA_TYPE_CHOICES = [
        (FILM, 'film'),
        (EPISODE, 'episode'),
        (MUSIC_VIDEO, 'music_video'),
        (VIDEO, 'video'),
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
    
    runtime =  models.PositiveSmallIntegerField() # runtime in minutes
    imdb_id = models.PositiveIntegerField()
    alt_title = models.CharField(max_length=1000, blank=True)
    language = models.CharField(max_length=1000, blank=True)
    colour = models.BooleanField(default=True)
    series = models.ForeignKey("MediaSeries", on_delete=models.CASCADE, blank=True, null=True)
    director = SortedManyToManyField(Person, related_name="director")#, through="DirectorThrough")
    stars = SortedManyToManyField(Person, related_name="stars")#, through="StarsThrough")
    genre = models.ManyToManyField(Genre)
    keywords = models.ManyToManyField(Keyword)
    description = models.TextField()
    alt_description = models.TextField()
    alt_versions = models.ManyToManyField('self', symmetrical=False)
    
# class SoundItem(MediaItem):
    # pass
    
# class PersonThrough(models.Model):
#     # intermediary table to allow VisionItem to return e.g. stars in order they were added
#     person = models.ForeignKey(Person, on_delete=models.CASCADE)
#     mediaitem = models.ForeignKey(VisionItem, on_delete=models.CASCADE)
#     created = models.DateTimeField(auto_now_add=True) 
    
# # bit of a hack, but i'm not sure how you're supposed to do this
# # if tyring to use PersonThrough as 'though' value for both stars and director, get this error:
# # mediabrowser.VisionItem: (models.E003) The model has two identical many-to-many relations through the intermediate model 'mediabrowser.PersonThrough'.
# class StarsThrough(PersonThrough): pass
# class DirectorThrough(PersonThrough): pass