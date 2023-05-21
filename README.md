# Pick

Pick is a media browser, built using django.

## Make DB

```
./manage.py makemigrations mediabrowser
./manage.py migrate
scripts/populate_db.py -f films.txt -p patch.csv
```

## Test

```
./manage.py test mediabrowser -v 2
```