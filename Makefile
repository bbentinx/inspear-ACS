COMPOSE := ./scripts/compose.sh

.PHONY: install up up-full down build logs test seed reset status fix-docker ready setup-genieacs dev-web purge-demo speedtest-file

install:
	chmod +x ./install.sh
	./install.sh

fix-docker:
	./scripts/fix-docker.sh

up: fix-docker
	$(COMPOSE) up -d --build

# Só backend (se build do web falhar no Docker Hub)
up-core: fix-docker
	$(COMPOSE) up -d --build postgres redis api worker

up-full: fix-docker
	$(COMPOSE) --profile genieacs up -d --build

# Ambiente completo TR-069 pronto para testar
ready:
	./scripts/ready_local.sh

setup-genieacs:
	./scripts/setup_genieacs.sh

watch-acs:
	./scripts/watch_acs.sh

dev-web:
	cd web && INTERNAL_API_URL=http://localhost:8000 npm run dev

purge-demo:
	./scripts/compose.sh exec -T postgres psql -U inspear -d inspear -c "DELETE FROM alerts; DELETE FROM diagnoses; DELETE FROM device_events; DELETE FROM device_snapshots; DELETE FROM devices; DELETE FROM customers;"
	@echo "Dados demo removidos — aguardando ONTs reais"

speedtest-file:
	chmod +x ./scripts/gen_speedtest_file.sh
	./scripts/gen_speedtest_file.sh

down:
	$(COMPOSE) --profile genieacs down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f api worker web

logs-all:
	$(COMPOSE) --profile genieacs logs -f

seed:
	./scripts/seed_demo.sh

test:
	./scripts/test_all.sh

reset:
	$(COMPOSE) --profile genieacs down -v
	$(COMPOSE) up -d --build
	sleep 20
	./scripts/seed_demo.sh

status:
	@echo "=== Containers ==="
	@$(COMPOSE) ps -a
	@echo ""
	@echo "=== Health ==="
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "API offline"
	@echo ""
	@echo "=== URLs ==="
	@echo "Painel:    http://localhost:3000  (admin@inspear.local / admin123)"
	@echo "API docs:  http://localhost:8000/docs"