# Mac Studio Tunnel Keepalive Scripts

Automated scripts to ensure Ollama and SSH tunnels stay running on both Mac Studios.

## What They Do

**M3 Mac Studio** (`m3_keepalive.sh`):
- Checks if Ollama is running, starts it if not
- Monitors SSH tunnel on port 11434 → droplet
- Restarts tunnel if connection dies
- Logs everything to `~/tunnel_keepalive_m3.log`

**M1 Mac Studio** (`m1_keepalive.sh`):
- Checks if Ollama is running, starts it if not
- Monitors SSH tunnel on port 12434 → droplet (Oracle/Vision)
- Restarts tunnel if connection dies
- Logs everything to `~/tunnel_keepalive_m1.log`

## Installation

### On M3 Mac Studio:

```bash
# 1. Create scripts directory
mkdir -p ~/mac_studio_scripts

# 2. Copy M3 script
cp m3_keepalive.sh ~/mac_studio_scripts/
chmod +x ~/mac_studio_scripts/m3_keepalive.sh

# 3. Install LaunchAgent
cp com.swaynesystems.m3.keepalive.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.swaynesystems.m3.keepalive.plist

# 4. Test it
~/mac_studio_scripts/m3_keepalive.sh
```

### On M1 Mac Studio:

```bash
# 1. Create scripts directory  
mkdir -p ~/mac_studio_scripts

# 2. Copy M1 script
cp m1_keepalive.sh ~/mac_studio_scripts/
chmod +x ~/mac_studio_scripts/m1_keepalive.sh

# 3. Install LaunchAgent
cp com.swaynesystems.m1.keepalive.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.swaynesystems.m1.keepalive.plist

# 4. Test it
~/mac_studio_scripts/m1_keepalive.sh
```

## Schedule

**Automatic Runs**:
- ✅ On system startup (login)
- ✅ Every 2 hours (7200 seconds)

**Times per day**: ~12 checks (every 2 hours for 24 hours)

## Logs

Check logs to see what's happening:

```bash
# M3
tail -f ~/tunnel_keepalive_m3.log

# M1
tail -f ~/tunnel_keepalive_m1.log
```

## Manual Control

```bash
# Stop the keepalive service
launchctl unload ~/Library/LaunchAgents/com.swaynesystems.m3.keepalive.plist

# Start it again
launchctl load ~/Library/LaunchAgents/com.swaynesystems.m3.keepalive.plist

# Force run right now (without waiting)
launchctl start com.swaynesystems.m3.keepalive
```

## What Gets Fixed Automatically

- ❌ **Ollama crashes** → Restarted
- ❌ **Tunnel disconnects** → Reconnected
- ❌ **After reboot** → Both start automatically
- ❌ **Stale connections** → Detected and refreshed

## Troubleshooting

**If tunnels keep failing:**
1. Check SSH keys are set up: `ssh root@165.22.146.182`
2. Check firewall isn't blocking: `sudo pfctl -s all`
3. Review logs for errors

**If Ollama won't start:**
1. Check if it's installed: `which ollama`
2. Try manual start: `ollama serve`
3. Check port 11434 isn't in use: `lsof -i :11434`

---

**Created**: December 2025  
**Maintains**: Swayne Systems AI Infrastructure
