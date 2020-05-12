DEPLOY_TGT := gwent
DEPLOY_TGT := 192.168.1.185

server_deploy:
	@echo "Deploying to $(DEPLOY_TGT)"
	@rsync -avzl --exclude=*.pyc -e ssh software ${DEPLOY_USER}@${DEPLOY_TGT}:~/thor/
	@ssh ${DEPLOY_USER}@${DEPLOY_TGT} bash -s < server_deploy.sh
