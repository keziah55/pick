# Pick

Pick is a media browser, built using django.

## Features

Hover over a thumbnail to see a description of the film:

![Pick main view](screenshots/main_view.png)

Filter films by year, runtime, black and while/colour, digital/physical
availability and by user rating:

![Search filters](screenshots/search_filters.png)

You can also filter by genre, using `AND`, `OR` and `NOT` filters. This allows
you to require or exclude genre(s):

![Genre filters](screenshots/genre_filters.png)

Films can be grouped into series. Click through to see all the series members

![Film series](screenshots/media_series.png)

## Install

```
python -m venv .venv
source .venv/bin/activate 
python -m pip install -r requirements.txt
```

You may need to either copy or link `el-pagination.js` from the venv into `static`, for example:
```
ln -s .venv/lib/python3.12/site-packages/el_pagination/static/el-pagination/js/el-pagination.js mediabrowser/static/mediabrowser/js/el-pagination.js
```

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

To view on another machine on the network, add the IP address to `ALLOWED_HOSTS` in settings.py.