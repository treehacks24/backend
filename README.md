
# Installation

```
poetry install
poetry shell
uvicorn main:app --reload
```


start redis db
```
docker run --name redis-db -p 6379:6379 -d redis redis-server --save 60 1 --loglevel warning
```


start mongo db (optional)
```
docker run --name db -p 27017:27017  -d mongo:latest
```




## Deploy

```
uvicorn main:app --host 0.0.0.0 --port 80
```
