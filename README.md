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

## Run on local network

```
./manage.py runserver 0.0.0.0:8000
```

To view on anthoer mahcine on the network, add the IP address to `ALLOWED_HOSTS` in settings.py.