## 🖥️ PC with NVIDIA GPU Support
If you have a powerful PC with an NVIDIA GPU, or a PC with a CPU that is many times more powerful than your PI, then you can use this Docker.
The calculations have been reduced from 20 minutes per song to 40 seconds, and the music folder can be integrated via a network drive. Both the PC and PI can work on the calculation in parallel.

Please also refer to the README file in the RPI5 folder.

**Prerequisite:**
* NVIDIA Container Toolkit is installed on the host.
* `Dockerfile.pc` is used in `docker-compose.yml`.
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## 🖥️ PC mit NVIDIA GPU Support
Wenn du einen Leistungsstarken PC mit NVIDIA-GPU hast, oder einen PC wo die CPU um ein vielfaches stärker ist als auf deinem PI, dann kannst du diesen Docker nutzen.
Die Berechnungen haben sich von 20 Minuten pro Lied auf 40 Sekunden verkürzt, den Musikordner kann man via Netzwerklaufwerk einbinden. Beide, PC und PI können parallel an der Berechnung arbeiten.

**Voraussetzung:**
* NVIDIA Container Toolkit ist auf dem Host installiert.
* In der `docker-compose.yml` wird das `Dockerfile.pc` verwendet.

Bitte beachte auch die README im RPI5 Ordner

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# NVIDIA Container Toolkit:

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

sudo nvidia-ctk runtime configure --runtime=docker

sudo systemctl restart docker

docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

