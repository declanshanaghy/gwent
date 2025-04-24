DEPLOY_USER := dshanaghy
DEPLOY_TGT := 192.168.1.225
DEPLOY_DIR := "~/gwent"

rsync:
	@echo "rsync to $(DEPLOY_TGT)"
	@rsync \
	    -avzl --delete \
	    --exclude=*.pyc \
		--exclude=software/gwent/.eggs \
	    --exclude *.egg-info \
	    --exclude __pycache__ \
	    -e ssh . ${DEPLOY_USER}@${DEPLOY_TGT}:${DEPLOY_DIR}/

install: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install.sh

install-app: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-app.sh

install-system: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-system.sh

update-service: rsync
	@echo "Update service $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/update-service.sh

rotary-rpigpio-test: rsync
	@echo "Running rotary_rpigpio entry point on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.rotary-rpigpio-test"

rotary-gpiozero-test: rsync
	@echo "Running rotary_gpiozero entry point on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.rotary-gpiozero-test"

rfid-test: rsync
	@echo "Running RFID scanner on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.rfid-test"

oled-ssd1306-test: rsync
	@echo "Running SSD1306 OLED display test on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.oled-ssd1306-test"

oled-ssd1305-pillow-test: rsync
	@echo "Running SSD1305 OLED Pillow demo on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.oled-ssd1305-pillow-test"

oled-ssd1305-luma-test: rsync
	@echo "Running SSD1305 OLED display with SSD1306 driver demo on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.oled-ssd1305-luma-test"

matrix-test: rsync
	@echo "Running matrix display test with TCA9548A multiplexer on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.matrix-test"

oled-test: rsync
	@echo "Running comprehensive OLED display test on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.oled-test"

oled-direct-test: rsync
	@echo "Running direct OLED display test on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.oled-direct-test"

display-diagnostic: rsync
	@echo "Running display diagnostic on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display-diagnostic"

game: rsync
	@echo "Running Gwent game on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.game.main"
