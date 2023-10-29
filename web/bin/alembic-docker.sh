docker compose run -v ${PWD}/alembic:/app/alembic -v ${PWD}/alembic.ini:/app/alembic.ini --rm digidive python3 -m alembic $@
