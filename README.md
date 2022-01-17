# Discord-Destiny-2-Server-Browser-Bot

A simple Discord bot that allows users to create Destiny 2 "lobbies" and then be seen in the bot's roster with the current capacity of each lobby.

This is still a work in progress, some testing still needs to be done and many things may break

# How to use
- Step 1: Insert both your discord token and bungie API key in their respective slots. You can also change the bot's prefix which is '--' by default
- Step 2: Run main.py

# Commands
Basic:
- create-lobby {bungie name} {optional voice channel id or any additional text}: creates a lobby that will be seen in the bot's roster
- close-lobby: will close the lobby you are currently leading if you are leading any
- transfer-lobby {new leader discord mention} {new leader bungie name}: transfers the lobby you are currently leading if you are leading any to another user

Admin:
- set-roster-channel: sets the channel in which this is called to be the location where the bot will automatically edit a single message to act as a server browser
- roster: sends the current roster, should preferrably not be used
