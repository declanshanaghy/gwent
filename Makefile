DEPLOY_USER := dshanaghy
SSH_KEY := ~/.ssh/id_rsa
# Home
DEPLOY_TGT := 192.168.1.225
#
# Benicia makerspace
# DEPLOY_TGT := 10.1.10.236

DEPLOY_DIR := "~/gwent"

.PHONY: rsync install install-app deploy start validate deploy-and-validate test-hardware deploy-and-test rotary-rpigpio-test rotary-gpiozero-test rfid-test oled-ssd1306-test oled-ssd1305-pillow-test oled-ssd1305-luma-test matrix-test oled-test oled-direct-test display-diagnostic game

rsync:
	@echo "rsync to $(DEPLOY_TGT)"
	@rsync \
	    -avzl --delete \
	    --exclude=*.pyc \
	    --exclude=software/gwent/.eggs \
	    --exclude *.egg-info \
	    --exclude __pycache__ \
	    -e "ssh -i $(SSH_KEY)" . ${DEPLOY_USER}@${DEPLOY_TGT}:${DEPLOY_DIR}/

install: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install.sh

install-app: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-app.sh

install-system: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-system.sh

update-service: rsync
	@echo "Update service $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/update-service.sh

# Deploy the application to the Raspberry Pi
deploy: install install-app
	@echo "Deployment complete!"

# Start/restart the gwent service
start:
	@echo "Starting/restarting gwent service on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "sudo systemctl restart gwent.service"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "sudo systemctl status gwent.service"

# Validate that gwent is running correctly
validate:
	@echo "Validating gwent on $(DEPLOY_TGT)"
	@./scripts/validate-gwent.sh

# Run hardware tests on the Raspberry Pi
test-hardware:
	@echo "Running hardware tests on $(DEPLOY_TGT)"
	@RASPBERRY_PI_IP=$(DEPLOY_TGT) DEPLOY_USER=$(DEPLOY_USER) SSH_KEY=$(SSH_KEY) ./scripts/deploy-and-test.sh

# Deploy and run hardware tests in one command
deploy-and-test: install-app test-hardware
	@echo "Deployment and hardware testing complete!"

# Deploy and validate in one command
deploy-and-validate: deploy start validate
	@echo "Deployment and validation complete!"

# POC script targets
rotary-rpigpio-test: rsync
	@echo "Running rotary_rpigpio entry point on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_rpigpio"

rotary-gpiozero-test: rsync
	@echo "Running rotary_gpiozero entry point on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_gpiozero"

rfid-test: rsync
	@echo "Running RFID scanner on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.rfid_tests.rfid"

oled-ssd1306-test: rsync
	@echo "Running SSD1306 OLED display test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.oled_test"

oled-ssd1305-pillow-test: rsync
	@echo "Running SSD1305 OLED Pillow demo on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.ssd1305_pillow_demo"

oled-ssd1305-luma-test: rsync
	@echo "Running SSD1305 OLED display with SSD1306 driver demo on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.ssd1305_luma_demo"

matrix-test: rsync
	@echo "Running matrix display test with TCA9548A multiplexer on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.TCA9548A-MatrixI2C-test"

oled-test: rsync
	@echo "Running comprehensive OLED display test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.oled_test"

oled-direct-test: rsync
	@echo "Running direct OLED display test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.TCA9548A-MatrixI2C-test"

display-diagnostic: rsync
	@echo "Running display diagnostic on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.TCA9548A-MatrixI2C-test"

game: rsync
	@echo "Running Gwent game on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.game.main"
