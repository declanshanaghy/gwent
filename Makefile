DEPLOY_USER := pi
DEPLOY_TGT := gwent
DEPLOY_TGT := 192.168.1.185

rsync:
	@echo "rsync to $(DEPLOY_TGT)"
	@rsync \
	    -avzl --delete \
	    --exclude=*.pyc \
	    --exclude *.egg-info \
	    --exclude __pycache__ \
	    -e ssh software ${DEPLOY_USER}@${DEPLOY_TGT}:~/gwent/

install: rsync
	@echo "Install to $(DEPLOY_TGT)"
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -s < install.sh
