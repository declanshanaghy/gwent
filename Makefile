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

rotary-rpigpio: rsync
	@echo "Running rotary_rpigpio entry point on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.rotary_rpigpio"

rotary-gpiozero: rsync
	@echo "Running rotary_gpiozero entry point on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.rotary_gpiozero"

rfid: rsync
	@echo "Running RFID scanner on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.rfid"

ssd1306: rsync
	@echo "Running SSD1306 OLED display test on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.ssd1306_luma_simpletest"

ssd1305: rsync
	@echo "Running SSD1305 OLED Pillow demo on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.ssd1305_pillow_demo"

ssd1305-luma: rsync
	@echo "Running SSD1305 OLED display with SSD1306 driver demo on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.ssd1305_luma_demo"

test-displays: rsync
	@echo "Running display test with TCA9548A multiplexer on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.test_displays"

game: rsync
	@echo "Running Gwent game on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.game.main"
