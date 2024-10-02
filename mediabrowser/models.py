from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from sortedm2m.fields import SortedManyToManyField


class BaseSlug(models.Model):
    """
    Model base class (essentially a mixin) to add and update a slug

    The slug will be generated from the Model's `name` field, or `title` if
    there is no `name`

    An exception is raised if neither field is present
    """

    slug = models.SlugField(default="", null=False, db_index=True)

    def save(self, *args, **kwargs):
        """Override `save` to set slug"""
        if (name := getattr(self, "name", None)) is None:
            if (name := getattr(self, "title", None)) is None:
                raise Exception("Model must contain 'name' or 'title' field")
        self.slug = slugify(name)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class MediaSeries(BaseSlug):
    title = models.CharField(max_length=200, primary_key=True, unique=True)

    def __str__(self):
        return self.title


class Person(models.Model):
    imdb_id = models.PositiveIntegerField(primary_key=True, unique=True)
    name = models.CharField(max_length=200)
    alias = models.CharField(max_length=200, null=True)

    def __str__(self):
        return f"{self.name} ({self.imdb_id})"


class Genre(models.Model):
    name = models.CharField(max_length=200, primary_key=True, unique=True)

    def __str__(self):
        return self.name


class Keyword(models.Model):
    name = models.CharField(max_length=200, primary_key=True, unique=True)

    def __str__(self):
        return self.name


class MediaItem(BaseSlug):
    FILM = "FILM"
    EPISODE = "EPISODE"
    MUSIC_VIDEO = "MUSIC_VIDEO"
    VIDEO = "VIDEO"
    SONG = "SONG"

    MEDIA_TYPE_CHOICES = [
        (FILM, "film"),
        (EPISODE, "episode"),
        (MUSIC_VIDEO, "music_video"),
        (VIDEO, "video"),
        (SONG, "song"),
    ]

    title = models.CharField(max_length=500)
    filename = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1900)])
    img = models.CharField(max_length=500)  # url to image
    local_img = models.ImageField(null=True)
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPE_CHOICES)

    def __str__(self):
        return f"{self.title} ({int(self.year)})"

    class Meta:
        abstract = True


class VisionItem(MediaItem):
    FILM = "FILM"
    EPISODE = "EPISODE"
    MUSIC_VIDEO = "MUSIC_VIDEO"
    VIDEO = "VIDEO"

    MEDIA_TYPE_CHOICES = [
        (FILM, "film"),
        (EPISODE, "episode"),
        (MUSIC_VIDEO, "music_video"),
        (VIDEO, "video"),
    ]

    runtime = models.PositiveSmallIntegerField()  # runtime in minutes
    imdb_id = models.PositiveIntegerField()
    alt_title = models.CharField(max_length=1000, blank=True)
    language = models.CharField(max_length=1000, blank=True)
    colour = models.BooleanField(default=True)
    series = models.ForeignKey("MediaSeries", on_delete=models.CASCADE, blank=True, null=True)
    director = SortedManyToManyField(
        Person, related_name="director"
    )  # , through="DirectorThrough")
    stars = SortedManyToManyField(Person, related_name="stars")  # , through="StarsThrough")
    genre = models.ManyToManyField(Genre)
    keywords = models.ManyToManyField(Keyword)
    description = models.TextField(blank=True)
    alt_description = models.TextField(blank=True)
    alt_versions = models.ManyToManyField("self", symmetrical=False)
    imdb_rating = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )
    user_rating = models.FloatField(
        default=3,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    bonus_features = models.BooleanField(default=False)
    digital = models.BooleanField(default=True)
    physical = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} ({int(self.year)})"


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
