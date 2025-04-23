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

update-service: rsync
	@echo "Update service $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -c ${DEPLOY_DIR}/scripts/update-service.sh

rotary-simple: rsync
	@echo "Running rotary_simple entry point on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && cd ${DEPLOY_DIR}/software/gwent && pip3 install -e . && python -m gwent.poc.rotary_simple"

rotary-gpiozero-simple: rsync
	@echo "Running rotary_gpiozero_simple entry point on $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} "source ~/gwent-venv/bin/activate && cd ${DEPLOY_DIR}/software/gwent && pip3 install -e . && python -m gwent.poc.rotary_gpiozero_simple"

