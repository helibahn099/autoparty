sudo apt update
sudo apt install docker.io docker-compose-v2 -y
sudo usermod -aG docker $USER
docker compose version
echo "alias dc='docker compose'" >> /home/$USER/.bashrc
source /home/$USER/.bashrc
docker compose version
