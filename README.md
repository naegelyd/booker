# Booker

A FastAPI service for managing rooms and bookings.

## Running Booker

To run, please run:

```sh
docker-compose up
```

This will start the postgres and web service(at http://0.0.0.0:8000/) containers.
For the read endpoints, you can access them directly(http://0.0.0.0:8000/rooms) but for the write endpoints, consider using the swagger UI at http://0.0.0.0:8000/docs or use something like curl or postman.

## Testing Booker

To test, please run:

```sh
docker-compose run web pytest booker
```