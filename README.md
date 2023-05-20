# Pick

Pick is a media browser, built using django.

## Make DB

```
./manage.py makemigrations mediabrowser
./manage.py migrate
./populate_db.py -f films.txt -p patch.csv
```