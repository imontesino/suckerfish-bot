# Suckerfish

The idea in this project is to have a pi zero stuck with double sided tape to the inside of your pc.
Its main functionality is to power and/or reset the bigger pc remotely.
My main use case is a dual boot system, where I have to remote into Ubuntu (ssh, TeamViewer, etc.)
for my work and into Windows for accessing a photo archive and gamestreaming via
[moonlight](https://moonlight-stream.org/).

<!-- TODO: Add Hardware instructions section -->
## Raspberry Pi Zero W Setup

Install raspbian buster image. Here is a convinient way:

Download and install [rpi-imager](https://www.raspberrypi.com/software/). This is a GUI tool to
easily install raspbian images. It also allows to setup of ssh keys and wifi before hand.

This [video](https://www.youtube.com/watch?v=om8gGB3gyT0) shows how to do it.

Choose the rasbian buster lite x32 image.

<!-- picture of the main menu -->

<!-- picture of the correct raspbian image-->

## Installation

If installed correctly you can now acess the pi zero via ssh.

```bash
ssh pi@suckerfish_hostname
```

Once there install some dependencies

```bash
sudo apt-get install git python3-pip
```

Geŋenerate an ssh key

```bash
ssh-keygen -t rsa -C "MyEmailAddress" -f ~/.ssh/id_rsa
```

Ssh from the pi to the pc to save the key

```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub your_username@pc_ip_address
```

Clone the repo to the home directory of the pi zero.

```bash
$ cd ~/
$ git clone https://github.com/imontesino/suckerfish-bot
```

Install the python dependencies.

```bash
$ cd ~/suckerfish-bot
$ pip3 install -r requirements.txt
```

Add your bot token to the config file.

Then copy the service file to the systemd folder.

```bash
$ sudo cp /home/pi/suckerfish_bot/resources/suckerfish_bot.service /etc/systemd/system/
```
