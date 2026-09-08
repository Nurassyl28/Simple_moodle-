.PHONY: up down logs psql reset

up:            ## поднять инфраструктуру
	docker compose up -d

down:          ## остановить (данные остаются)
	docker compose down

logs:          ## логи
	docker compose logs -f

psql:          ## консоль Postgres
	docker compose exec postgres psql -U $$(grep POSTGRES_USER .env | cut -d= -f2) -d $$(grep POSTGRES_DB .env | cut -d= -f2)

reset:         ## снести БД вместе с данными и накатить схему заново
	docker compose down -v
	docker compose up -d
