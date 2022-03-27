# Suckerfish

The idea in this project is to have a pi zero stuck with double sided tape to the inside of your pc.
Its main functionality is to power and/or reset the bigger pc remotely.
My main use case is a dual boot system, where I have to remote into Ubuntu (ssh, TeamViewer, etc.)
for my work and into Windows for accessing a photo archive and gamestreaming via
[moonlight](https://moonlight-stream.org/).

<!-- TODO: Add Hardware instructions section -->

## Installation

Clone the repo to the home directory of the pi zero.

```bash
cd ~/
git clone https://github.com/imontesino/suckerfish-bot
```

Install the python dependencies.

```bash
cd ~/suckerfish-bot
pip3 install -r requirements.txt
```

Add your bot token to the config file.

Then copy the service file to the systemd folder.

```bash
sudo cp /home/pi/suckerfish_bot/suckerfish_bot.service /etc/systemd/system/
```
