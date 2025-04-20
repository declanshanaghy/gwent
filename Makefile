DEPLOY_USER := geralt
# Home
# DEPLOY_TGT := living-room-pi.lan
#
# Benicia makerspace
DEPLOY_TGT := 10.1.10.236 

DEPLOY_DIR := "~/gwent"

rsync:
	@echo "rsync to $(DEPLOY_TGT)"
	@rsync \
	    -avzl --delete \
	    --exclude=*.pyc \
	    --exclude *.egg-info \
	    --exclude __pycache__ \
	    -e ssh . ${DEPLOY_USER}@${DEPLOY_TGT}:${DEPLOY_DIR}/

install: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/install.sh

install-app: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/install-app.sh
