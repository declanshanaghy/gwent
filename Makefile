DEPLOY_USER := pi
DEPLOY_TGT := gwent
DEPLOY_TGT := 192.168.1.185

deploy:
	@echo "Deploying to $(DEPLOY_TGT)"
	@rsync -avzl --exclude=*.pyc -e ssh software ${DEPLOY_USER}@${DEPLOY_TGT}:~/gwent/
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -s < deploy.sh
