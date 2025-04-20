DEPLOY_USER := dshanaghy
SSH_KEY := ~/.ssh/id_rsa
# Home
DEPLOY_TGT := 192.168.1.225
#
# Benicia makerspace
# DEPLOY_TGT := 10.1.10.236

DEPLOY_DIR := "~/gwent"

.PHONY: rsync install install-app deploy start validate deploy-and-validate

rsync:
	@echo "rsync to $(DEPLOY_TGT)"
	@rsync \
	    -avzl --delete \
	    --exclude=*.pyc \
	    --exclude *.egg-info \
	    --exclude __pycache__ \
	    -e "ssh -i $(SSH_KEY)" . ${DEPLOY_USER}@${DEPLOY_TGT}:${DEPLOY_DIR}/

install: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/install.sh

install-app: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/install-app.sh

# Deploy the application to the Raspberry Pi
deploy: install
	@echo "Deployment complete!"

# Start/restart the gwent service
start:
	@echo "Starting/restarting gwent service on $(DEPLOY_TGT)"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "sudo systemctl restart gwent.service"
	@ssh -i $(SSH_KEY) ${DEPLOY_USER}@${DEPLOY_TGT} "sudo systemctl status gwent.service"

# Validate that gwent is running correctly
validate:
	@echo "Validating gwent on $(DEPLOY_TGT)"
	@./validate-gwent.sh

# Deploy and validate in one command
deploy-and-validate: deploy start validate
	@echo "Deployment and validation complete!"
