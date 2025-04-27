DEPLOY_USER := dshanaghy
SSH_KEY := ~/.ssh/id_rsa
# Home
DEPLOY_TGT := 192.168.1.225
#
# Benicia makerspace
# DEPLOY_TGT := 10.1.10.236

DEPLOY_DIR := "~/gwent"

.PHONY: rsync install install-app install-system install-service deploy start validate deploy-and-validate test-hardware deploy-and-test rotary-rpigpio-test rotary-gpiozero-test rotary-diagnostic-test rotary-pin-test rotary-debounce-test rotary-diagnostics rotary-robust rotary-lgpio rotary-pigpio rotary-test gpio-check gpio-service-stop gpio-service-start rfid-test oled-ssd1306-test oled-ssd1305-pillow-test oled-ssd1305-luma-test matrix-test oled-test oled-direct-test display-diagnostic mfd-diagnostic audio-diagnostic game read-card-util write-card-util validate-cards write-cards-to-disk read-card-file get-random-card download-skellige-cards download-skellige-cards-local

rsync:
	@echo "rsync to $(DEPLOY_TGT)"
	@rsync \
	    -talvx \
		--delete \
	    --exclude=software/data/cards \
	    --exclude=*.pyc \
	    --exclude=software/gwent/.eggs \
	    --exclude .git \
	    --exclude *.egg-info \
	    --exclude __pycache__ \
	    -e "ssh -i $(SSH_KEY)" . ${DEPLOY_USER}@${DEPLOY_TGT}:${DEPLOY_DIR}/

install: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install.sh

install-app: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-app.sh

install-venv: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-venv.sh

install-system: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-system.sh

install-service: rsync
	@echo "Installing gwent service on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/install-service.sh

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

rotary-diagnostic: rsync
	@echo "Running rotary encoder diagnostic tool on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_diagnostic"

rotary-pin-test: rsync
	@echo "Running rotary encoder pin configuration test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_pin_test"

rotary-debounce-test: rsync
	@echo "Running rotary encoder debounce test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_debounce_test"

rotary-diagnostics: rsync
	@echo "Running comprehensive rotary encoder diagnostics on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.run_rotary_diagnostics"

rotary-robust: rsync
	@echo "Running robust rotary encoder test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_robust"

rotary-lgpio: rsync
	@echo "Running lgpio rotary encoder test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_lgpio"

rotary-pigpio: rsync
	@echo "Running pigpio rotary encoder test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.rotary_pigpio"

rotary-test: rsync
	@echo "Running rotary encoder implementation test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.input_tests.test_rotary_implementations"

gpio-check: rsync
	@echo "Running GPIO permissions and usage check on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.diagnostic_tools.gpio_permissions_check"

gpio-service-stop: rsync
	@echo "Stopping GPIO service on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.diagnostic_tools.gpio_service_manager --action stop"

gpio-service-start: rsync
	@echo "Starting GPIO service on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.diagnostic_tools.gpio_service_manager --action start"

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

TCA9548A-MatrixI2C-test: rsync
	@echo "Running direct OLED display test on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.display_tests.TCA9548A-MatrixI2C-test"

mfd-diagnostic: rsync
	@echo "Running MFD diagnostic tool on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.diagnostic_tools.mfd_diagnostic"

game: rsync start
	@echo "Deploying and running Gwent game on $(DEPLOY_TGT)"
	@echo "Streaming logs (press Ctrl+C to stop)..."
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "journalctl -fu gwent"

audio-diagnostic: rsync
	@echo "Running audio diagnostic tool on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.diagnostic_tools.audio_diagnostic"

read-card-util: rsync
	@echo "Running card reader utility on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.util.read_write_cards read"

write-card-util: rsync
	@echo "Running card reader utility on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.util.read_write_cards write"

card-manager: rsync
	@echo "Running card manager utility on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && python -m gwent.poc.util.card_manager"

validate-cards: rsync
	@echo "Validating cards on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && validate-cards"

write-cards-to-disk: rsync
	@echo "Writing all cards to disk on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && write-cards-to-disk"

read-card-file: rsync
	@echo "Reading card file on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && read-card-file"

get-random-card: rsync
	@echo "Getting random card on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && get-random-card"

download-tmp-from-pi:
	@echo "rsync from $(DEPLOY_TGT)"
	@rsync \
	    -talvx \
	    -e "ssh -i $(SSH_KEY)" ${DEPLOY_USER}@${DEPLOY_TGT}:${DEPLOY_DIR}/tmp/* ./tmp/

download-cards-from-pi:
	@echo "rsync from $(DEPLOY_TGT)"
	@rsync \
	    -talvx \
	    -e "ssh -i $(SSH_KEY)" ${DEPLOY_USER}@${DEPLOY_TGT}:${DEPLOY_DIR}/software/data/cards/* ./software/data/cards/

download-skellige-cards-to-pi: rsync
	@echo "Downloading and comparing Skellige cards from Witcher Wiki"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} \
		"cd ${DEPLOY_DIR} && \
		source ~/gwent-venv/bin/activate && \
		python -m gwent.poc.util.card_downloader_witcher_fandom_com"
