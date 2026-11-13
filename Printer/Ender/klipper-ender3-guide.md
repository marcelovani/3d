# Klipper on an Ender 3 Pro with a Raspberry Pi

Nov 7–8, 2026 · @Marcelo

## Read this first

These cost us most of two days. Knowing them up front saves almost all of it.

1. **The printer flashes the first file on the SD card, whatever its name.** It isn't looking for `.bin`. A card with Pi files on it gets a text file flashed, and the board stops working. Use a card holding only the firmware (Step 7).
2. **The printer's board runs on USB power.** With the USB cable plugged in, switching the printer off and on doesn't restart the board. Unplug the USB cable to make it read the card.
3. **Some USB cables only charge.** The printer's screen lights up, but no data gets through. If the Pi doesn't list `CH340` in its USB devices, swap the cable.
4. **Find out which chip the board has before building firmware** (see _Identify the printer's board_). Ours was a V4.2.2 with a GD32F303RET6 chip, not the STM32 most guides assume.
5. **An old Pi crashing mid-install silently deletes files** (drivers, Python packages). If something that worked stops working after a crash, reinstall it (see _If the Pi crashes or loses power_).
6. **After the Pi boots, Klipper can start before the printer's USB port appears** and need a FIRMWARE RESTART. The boot delay in Step 8 fixes it.
7. **The bootloader explains itself.** It prints what it's doing over USB at 115200 baud, and recording that ended hours of guessing (Step 7).

## What happened, in order

So you can see which problems come in which order:

1. Desktop Pi OS too slow on a Pi Model B, so we switched to Lite.
2. The USB Wi-Fi dongle hung the first boot, so we used Ethernet.
3. Installed Klipper, Moonraker and Mainsail (Steps 3–5). Built firmware on the Mac with Docker (Step 6).
4. The Pi crashed a few times; Wi-Fi drivers and a Moonraker Python package vanished. Reinstalled both.
5. Got the dongle working: driver reinstalled, power-save off, moved to the other USB port.
6. Mainsail loaded but said `mcu 'mcu': Unable to connect`. The Pi saw no printer on USB: the cable was charge-only. A new cable fixed that.
7. Then `No communication with MCU`. The board was stuck in its bootloader. Four flashes failed, because the bootloader flashed Pi files (`cmdline.txt`, `ISSUE.TXT`) from the card instead of the firmware.
8. Recorded the bootloader's messages from the Mac, which showed exactly that. Flashed with a card holding only the firmware, after replugging the USB cable to restart the board. It worked.
9. Mainsail: **Ready**, after one FIRMWARE RESTART.
10. Added Mainsail's macros and a boot delay for Klipper (Step 8). Homed all axes and heated the nozzle to 180°C and the bed to 50°C: all fine.
11. Loading the filament took about 400 mm through the tube; old black filament came out before the green.
12. Line test good. First cube stopped while homing: `Timer too close`, the Pi out of memory. Fixed with `gpu_mem=16` and Klipper priority.
13. Next cube: first layer didn't stick in the middle. Paper test at the centre (`Z_ENDSTOP_CALIBRATE`), then two live adjustments, saved: final `position_endstop: -0.150`. The cube printed.

## What you need

One SD card is enough, because the printer only needs it once, to flash the firmware. A spare card makes that flash much simpler (Step 7). After that you print from a web page.

| Item | What we used | Check |
| --- | --- | --- |
| Printer | Creality Ender 3 Pro, board V4.2.2, chip GD32F303RET6 | USB port on the side: micro-USB = 4.2.x board, mini-USB = 1.1.x. Chip: see _Identify the printer's board_ |
| Raspberry Pi | Raspberry Pi Model B Rev 1 (we thought it was a Pi 2) | Run `tr -d '\0' < /proc/device-tree/model` once logged in |
| SD card | One 32 GB microSD, shared by the Pi and the printer | It gets erased, so copy any files off it first. A second, spare card makes Step 7 much simpler |
| Network | Ethernet first; later a D-Link DWL-G122 USB Wi-Fi dongle | The dongle needs the fixes in _Wi-Fi with a USB dongle_ |
| Power | 5V 2.5A supply for the Pi | Never power the Pi from the printer or a laptop |
| USB cable | Micro-USB **data** cable, Pi to printer | Charge-only cables light the printer's screen but carry no data |
| Mac | Docker running | Used to build the firmware fast |

The Pi's user is `admin`, set in Step 1. Our Pi: `ender.local`.

A Pi 3, Pi 4 or Pi Zero 2 W is recommended. The original Model B (1 core, 256 MB) works, but slowly.

## Step 1: Write the SD card

Use Raspberry Pi Imager and pick **Lite**. The desktop version is far too slow on an old Pi.

1. Download Imager from [raspberrypi.com/software](https://www.raspberrypi.com/software/).
2. Put the SD card in the Mac.
3. Device: your Pi model.
4. OS: **Raspberry Pi OS (other) → Raspberry Pi OS Lite (32-bit)**.
5. Storage: the SD card.
6. Fill in every customisation setting:
   1. Hostname: `ender`
   2. Username and password (we used `admin`).
   3. Wi-Fi: only if you'll use it. We used Ethernet.
   4. SSH: **on**.
7. Write the card and wait until Imager ejects it.

## Step 2: First boot and log in

1. Put the card in the Pi. Plug in the Ethernet cable, then the power.
2. Wait 3 minutes. The first boot is slow.
3. On the Mac, find the Pi:
   1. By name: `ping ender.local`
   2. Without the name: `dns-sd -B _ssh._tcp`, or `nmap -p 22 --open 192.168.0.0/24`
4. Copy the Mac's key to the Pi, so you never type the password again: `ssh-copy-id admin@ender.local`
5. Log in: `ssh admin@ender.local`

Our Pi was at `192.168.0.26` on Ethernet, then `192.168.0.241` on Wi-Fi. `ender.local` always works.

If the Pi answers ping but SSH says "connection refused", SSH is off. Ours switched itself on after a minute. If yours doesn't, plug in a keyboard and run `sudo raspi-config`, then go to Interface Options → SSH.

## Wi-Fi with a USB dongle

Our dongle: D-Link DWL-G122 rev C1 (USB id `07d1:3c03`, Ralink RT2571W chip, driver `rt73usb`). Set up Ethernet first and switch to Wi-Fi once everything works. Three problems, in the order we hit them:

1. **No `wlan0`, although `lsusb` lists the dongle.** The driver files were missing, deleted by a crash (see _If the Pi crashes or loses power_). Reinstall the kernel package, which takes about 10 minutes:

   ```
   sudo apt-get install --reinstall linux-image-$(uname -r)
   sudo depmod -a && sudo modprobe rt73usb
   ```
2. **Connects, then drops after about 20 seconds.** The NetworkManager log says `link timed out`, then `ssid-not-found`. `sudo dmesg` shows `Device failed to wakeup` and `Vendor Request 0x07 failed ... error -71`. The dongle goes into power-save and can't wake up, a known bug in the old `rt73usb` driver. Turn power-save off by creating `/etc/NetworkManager/conf.d/wifi-powersave-off.conf`:

   ```
   [connection]
   wifi.powersave = 2
   ```

   Then `sudo systemctl restart NetworkManager`.
3. **The dongle disappears from `lsusb`.** `dmesg` shows `device descriptor read/64, error -71` and `unable to enumerate USB device`. Error -71 almost always means not enough power. The Model B's USB ports give very little current. Moving the dongle to the other USB port fixed it. Reloading the driver made it worse.

The Pi gets a new address on Wi-Fi (ours went from `192.168.0.26` to `192.168.0.241`). Use `ender.local`, which follows it.

## How to put files on the Pi

Steps 4, 5 and 8 create config files on the Pi. Both ways below work over Wi-Fi or Ethernet, as long as the Mac and the Pi are on the same network.

1. **Edit on the Pi:** log in with `ssh admin@ender.local`, then open the file, e.g. `sudo nano /etc/systemd/system/klipper.service`. Paste the text, then press Ctrl+O, Enter, Ctrl+X to save and quit. Use `sudo` only for files outside your home folder.
2. **Copy from the Mac:** save the file on the Mac, then `scp printer.cfg admin@ender.local:~/printer_data/config/`. For a system file, copy it to `~/` first, then on the Pi run `sudo mv ~/klipper.service /etc/systemd/system/`.

## Watching what the Pi is doing

Run these on the Pi after `ssh admin@ender.local`.

| Command | Shows |
| --- | --- |
| `free -h` | Memory used and free |
| `vmstat 2` | CPU and memory every 2 seconds. `us` = % CPU used, `id` = % idle, `si`/`so` above 0 = swapping to the SD card |
| `uptime` | Load. With 1 core, above 1.0 means busy |
| `tail -f ~/printer_data/logs/klippy.log` | Klipper's log, live |
| `tail -f ~/printer_data/logs/moonraker.log` | Moonraker's log, live |
| `systemctl status klipper moonraker nginx` | Whether each service is running |
| `vcgencmd get_throttled` | Power problems. Anything other than `0x0` = weak power supply |

**Watching a long install.** Steps 4 and 5 take up to an hour on an old Pi. Put the commands in a script and run it in the background with a log, so it keeps going if your SSH connection drops or the Mac sleeps:

```
nohup bash ~/step2.sh > ~/step2.log 2>&1 &
tail -f ~/step2.log
```

`tail -f` shows each new line as the install prints it. Ctrl+C stops the watching, not the install.

Ctrl+C stops a live command.

## Step 3: Prepare the Pi

Run these on the Pi once.

1. Let `sudo` run without a password, the Pi OS default:

   ```
   echo "admin ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/010_admin-nopasswd
   sudo chmod 440 /etc/sudoers.d/010_admin-nopasswd
   ```
2. Add 1 GB of swap. A Pi with 256 MB of RAM runs out of memory while installing without it:

   ```
   sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
   sudo mkswap /swapfile && sudo swapon -p 10 /swapfile
   echo "/swapfile none swap sw,pri=10 0 0" | sudo tee -a /etc/fstab
   ```
3. Install the basics:

   ```
   sudo apt-get update
   sudo apt-get install -y git unzip nginx
   ```

## Step 4: Install Klipper and Moonraker

Klipper is the printer software. Moonraker lets the web page talk to it.

Don't use Klipper's own `install-debian.sh` on an old Pi. It installs the ARM compilers, which takes over an hour. We build the firmware on the Mac instead (Step 6).

1. Get Klipper and its Python packages:

   ```
   cd ~ && git clone --depth 1 https://github.com/Klipper3d/klipper
   sudo apt-get install -y python3-venv python3-dev libffi-dev build-essential libncurses-dev libusb-1.0-0 pkg-config
   mkdir -p ~/printer_data/{config,logs,comms,gcodes}
   python3 -m venv ~/klippy-env
   ~/klippy-env/bin/pip install -r ~/klipper/scripts/klippy-requirements.txt
   ```
2. Create `/etc/systemd/system/klipper.service`:

   ```
   [Unit]
   Description=Klipper 3D printer host
   After=network-online.target
   [Service]
   User=admin
   ExecStart=/home/admin/klippy-env/bin/python /home/admin/klipper/klippy/klippy.py /home/admin/printer_data/config/printer.cfg -I /home/admin/printer_data/comms/klippy.serial -l /home/admin/printer_data/logs/klippy.log -a /home/admin/printer_data/comms/klippy.sock
   Restart=always
   RestartSec=10
   [Install]
   WantedBy=multi-user.target
   ```
3. Turn it on: `sudo systemctl daemon-reload && sudo systemctl enable klipper`
4. Install Moonraker:

   ```
   cd ~ && git clone --depth 1 https://github.com/Arksine/moonraker
   ./moonraker/scripts/install-moonraker.sh
   ```

On our Pi Model B this step takes 30–60 minutes.

## Step 5: Install Mainsail, the web page

1. Download Mainsail:

   ```
   mkdir -p ~/mainsail && cd ~/mainsail
   wget -q https://github.com/mainsail-crew/mainsail/releases/latest/download/mainsail.zip
   unzip -o mainsail.zip && rm mainsail.zip
   chmod o+x /home/admin
   ```
2. Replace `/etc/nginx/sites-enabled/default` with:

   ```
   server {
     listen 80 default_server;
     root /home/admin/mainsail;
     index index.html;
     location / { try_files $uri $uri/ /index.html; }
     location /websocket {
       proxy_pass http://127.0.0.1:7125/websocket;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_read_timeout 86400;
     }
     location ~ ^/(printer|api|access|machine|server)/ {
       proxy_pass http://127.0.0.1:7125$request_uri;
       proxy_set_header Host $http_host;
       proxy_set_header X-Real-IP $remote_addr;
     }
   }
   ```
3. In `~/printer_data/config/moonraker.conf`, let your home network in:

   ```
   [authorization]
   trusted_clients:
       192.168.0.0/16
       127.0.0.1
   cors_domains:
       *.local
       http://192.168.0.26
       http://192.168.0.241
   ```
4. Restart both: `sudo systemctl restart nginx moonraker`
5. Open `http://ender.local` on the Mac.

**Check the socket line.** Moonraker's installer writes `klippy_uds_address: /tmp/klippy_uds` under `[server]`. It must match the `-a` path in `klipper.service`, otherwise the web page can't reach Klipper:

```
klippy_uds_address: /home/admin/printer_data/comms/klippy.sock
```

Right after a restart the page can show "502 Bad Gateway" for up to a minute while Moonraker starts. Just wait.

## Identify the printer's board

The firmware must match the chip. Check it before Step 6.

1. Switch the printer off and unplug it from the wall.
2. The main board is in the metal box on the right of the base, under the screen, with the USB port on its side. The board behind the screen itself is the display's (ours says `12864ZW-10`), so ignore that one.
3. Lay the printer on its side and undo the screws on the underside of that box. The fan stays wired to the cover, so lift it gently.
4. The board version is printed on the board, e.g. `V4.2.2`.
5. The chip is the black square, about 1 cm across, in the middle. Read its first line:

| Chip | Klipper settings |
| --- | --- |
| STM32F103RET6 | Step 6 as written |
| GD32F303RET6 (ours) | Step 6 as written. It needs "Disable SWD", which is already in |
| HC32F460 | Different: choose HC32F460 in `make menuconfig`, and the card file goes in `/user/firmware.bin`. Step 6's settings won't work |

## Step 6: Build the printer firmware with Docker on the Mac

On the Mac this takes about a minute. On an old Pi, installing the compiler alone takes over an hour.

The firmware must come from the same Klipper version as the Pi, so it builds from the Pi's commit.

1. Make sure Docker is running: `docker info`
2. Make a folder and save this as `build.sh` in it:

   ```
   set -e
   apt-get update -qq
   apt-get install -y -qq git make gcc python3 gcc-arm-none-eabi binutils-arm-none-eabi libnewlib-arm-none-eabi
   git clone -q https://github.com/Klipper3d/klipper /src && cd /src && git checkout -q "$SHA"
   cat > .config <<CFG
   CONFIG_LOW_LEVEL_OPTIONS=y
   CONFIG_MACH_STM32=y
   CONFIG_MACH_STM32F103=y
   CONFIG_STM32_FLASH_START_7000=y
   CONFIG_STM32_SERIAL_USART1=y
   CONFIG_SERIAL_BAUD=250000
   CONFIG_STM32F103GD_DISABLE_SWD=y
   CFG
   make olddefconfig && make -j4
   cp out/klipper.bin /out/
   ```
3. In that folder, run:

   ```
   SHA=$(ssh admin@ender.local 'git -C ~/klipper rev-parse HEAD')
   docker run --rm -e SHA=$SHA -v "$PWD":/out debian:trixie bash /out/build.sh
   ```
4. You get `klipper.bin`, about 41 KB.

The Docker image is the official **`debian:trixie`** from Docker Hub, the same Debian version as Raspberry Pi OS. Docker downloads it by itself the first time, so there's nothing to install beforehand. It starts empty: `build.sh` installs the ARM compiler inside it, and `--rm` deletes the container when it finishes.

These settings suit the Creality 4.2.2 and 4.2.7 boards: STM32F103, 28KiB bootloader, serial on USART1 (PA10/PA9), 250000 baud. Some newer boards use a GD32 or HK32 chip instead. Those need **Disable SWD at startup** (`CONFIG_STM32F103GD_DISABLE_SWD=y`), which is harmless on a real STM32, so it's always on here.

**Check the versions match.** If the Pi is up but you can't SSH in, read its Klipper commit from the web API instead: `curl -s http://ender.local/printer/info` and look at `software_version` (ours was `af81d23`). Then build from that commit.

## Step 7: Flash the printer

The printer reads the firmware from an SD card once, when its board starts.

**The card must hold the firmware file and nothing else.** Our board's bootloader (4.2.2, GD32F303 chip) doesn't look for a `.bin` file. It flashes the **first file it finds**, whatever its name. On the Pi's card it flashed `cmdline.txt` and then `ISSUE.TXT`, which left the board stuck in a loop. This cost us four failed flashes.

**Unplug the USB cable to restart the board.** The 4.2.2 board also runs on power from the USB cable. While the cable is plugged into a Pi or Mac, switching the printer off and on doesn't restart the board, so it never reads the card.

With a spare microSD (FAT32, empty apart from the firmware) it's simple:

1. Copy `klipper.bin` onto it under a **new name** each time, e.g. `fw-20261108.bin`. The printer skips a name it has flashed before.
2. Copy it with `cp -X` and run `dot_clean -m /Volumes/<card>` afterwards. Otherwise macOS adds a hidden `._fw-....bin` file, which the bootloader can pick instead.
3. Unplug the printer's USB cable, put the card in the printer and switch it on. Wait 30 seconds.
4. Switch off and take the card out.

**With only the Pi's card**, empty its boot partition for the flash and restore it afterwards:

1. Shut down the Pi (`sudo shutdown now`), wait for the green light to stop, and put its card in the Mac. It shows up as **bootfs**.
2. Back up the boot partition: `cp -Rp /Volumes/bootfs/. ~/bootfs-backup/`
3. Erase it: `diskutil eraseVolume FAT32 BOOTFS disk8s1` (check the disk number with `diskutil list` first). Only the 512 MB boot partition is erased. The Pi's system partition is untouched, and the Pi still finds it, because `cmdline.txt` points to it by partition ID.
4. Copy only the firmware onto it, as in steps 1–2 above. Eject.
5. Flash as in steps 3–4 above.
6. Back in the Mac: erase the partition again, then `cp -RX ~/bootfs-backup/. /Volumes/BOOTFS/` and `dot_clean -m /Volumes/BOOTFS`. Check with `diff -rq` against the backup.
7. Put the card back in the Pi and power it on.

**Watching the flash.** The bootloader reports what it does over USB at 115200 baud. With the printer's USB cable in the Mac, record it with pyserial, then replug the cable to restart the board. Plain `cat` on the port is unreliable, because macOS resets the speed. Save this as `cap.py`:

```
import serial, sys, time, glob
log = open(sys.argv[1], "ab", buffering=0)
while True:
    ports = glob.glob("/dev/cu.usbserial*")
    if not ports:
        time.sleep(0.5); continue
    try:
        s = serial.Serial(ports[0], 115200, timeout=1)
        log.write(b"\n[open]\n")
        while True:
            d = s.read(256)
            if d: log.write(d)
    except Exception:
        log.write(b"\n[closed]\n"); time.sleep(0.5)
```

Run it, and watch the log in a second Terminal. It reconnects by itself when you replug the cable:

```
python3 -m venv v && v/bin/pip install pyserial
v/bin/python cap.py boot.log
tail -f boot.log
```

What the messages mean:

| Bootloader says | Meaning |
| --- | --- |
| `read file name : ISSUE.TXT` then `Need Update,Run Update` | It's flashing the wrong file. Leave only the firmware on the card |
| `App no Running !` then `Update failed, No SD/TF-Card or error` repeating | No working firmware. It loops until a good flash |
| `open file sucessful..`, `APP runing (addr :0x8007000)`, then silence | Flashed and running. Klipper is on the board |

Only the **first** flash needs the card moved by hand. Once Klipper is running, later firmware updates can go over the network: leave a card in the printer's slot and run `~/klipper/scripts/flash-sdcard.sh /dev/serial/by-id/<your port> creality-v4.2.7` on the Pi (use `creality-v4.2.2` for that board). This needs Klipper's `make` build on the Pi, or a `klipper.bin` copied there with `scp`.

## Step 8: Connect and test

The printer doesn't boot from the Pi. Each one starts on its own. The printer waits, and the Pi connects to it over USB.

1. Connect the USB cable from the Pi to the printer's micro-USB port.
2. Switch on the printer first, then the Pi.
3. Find the printer's port: `ls /dev/serial/by-id/`
4. Use Klipper's Ender 3 Pro config:

   ```
   cp ~/klipper/config/printer-creality-ender3pro-2020.cfg ~/printer_data/config/printer.cfg
   ```
5. In `printer.cfg`, set the `[mcu]` line to the port from step 3:

   ```
   [mcu]
   serial: /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
   ```
6. Add Mainsail's own macro file. Without it Mainsail warns `gcode_macro pause is not defined in config` (and the same for `resume` and `cancel_print`):

   ```
   curl -sL -o ~/printer_data/config/mainsail.cfg https://raw.githubusercontent.com/mainsail-crew/mainsail-config/master/client.cfg
   ```

   Then add this line to `printer.cfg`. The file already contains `[virtual_sdcard]`, `[pause_resume]` and `[display_status]`, so don't add those separately:

   ```
   [include mainsail.cfg]
   ```
7. Make Klipper wait for the printer at boot. Otherwise, on an old Pi, it starts before the printer's USB port appears, or while the Pi is still busy (`Timer too close`), and needs a FIRMWARE RESTART every time. Create `/etc/systemd/system/klipper.service.d/wait-for-printer.conf`:

   ```
   [Service]
   ExecStartPre=/bin/sh -c 'for i in $(seq 1 120); do [ -e /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 ] && break; sleep 1; done; sleep 30'
   TimeoutStartSec=300
   ```

   Then `sudo systemctl daemon-reload`. Klipper now starts about 30 seconds after the printer appears.
8. Add the bed screw positions to `printer.cfg`, so Klipper can walk the nozzle to each levelling knob (Step 9). These are for the stock Ender 3 Pro bed:

    ```
    [bed_screws]
    screw1: 30.5, 37
    screw1_name: front left
    screw2: 204.5, 37
    screw2_name: front right
    screw3: 204.5, 207
    screw3_name: back right
    screw4: 30.5, 207
    screw4_name: back left
    ```
9. Start Klipper: `sudo systemctl restart klipper`
10. Open `http://ender.local`. It should say **Ready**.
11. Test without filament: home all axes (`G28`), then heat the nozzle to 180°C and the bed to 50°C, and check both reach it. Ours did: the nozzle took about 80 seconds, the bed about 2 minutes. Then `TURN_OFF_HEATERS`.

If Mainsail shows an error instead of Ready, fix the cause and click **FIRMWARE RESTART** (or type `FIRMWARE_RESTART` in the console). The errors we got, and what they meant:

| Mainsail says | Meaning | Fix |
| --- | --- | --- |
| `mcu 'mcu': Unable to connect` | The Pi can't see the printer on USB at all | Different USB cable. Ours was charge-only: the printer's display had power, but no data got through |
| `No communication with MCU` / `Timeout on connect` in `klippy.log` | The Pi sees the port, but the board doesn't answer | The firmware isn't running. Reflash (Step 7) with only the firmware on the card |
| `mcu 'mcu': Unable to connect` right after the Pi boots, although the cable is fine | Klipper started before the printer's USB port appeared | FIRMWARE RESTART |
| `Timer too close` right after the Pi boots | The old single-core Pi is too busy while it boots | FIRMWARE RESTART once the Pi has settled |

## Step 9: Level the bed and print

The Ender 3 Pro has four knobs under the bed. Klipper moves the nozzle over each one in turn and waits while you adjust it. You need a sheet of plain printer paper.

1. Heat the bed to printing temperature, so it levels as it will print: `M140 S50` (PLA). Wait until it's there.
2. Home: `G28`.
3. Start the helper: `BED_SCREWS_ADJUST`. The nozzle moves over the first knob and drops to Z 0.
4. Slide the paper between the nozzle and the bed. Turn that corner's knob until the paper drags slightly as you move it, but doesn't tear or catch.
5. Type `ADJUSTED` if you turned the knob, or `ACCEPT` if it was already right. The nozzle moves to the next knob.
6. Once all four are done, the helper goes round again. Repeat until you can `ACCEPT` all four in a row. Adjusting one corner shifts the others slightly, so expect two or three rounds.

Ours took two rounds: all four knobs needed turning in the first, and none in the second.

**Then set the height in the middle of the bed.** Levelling the corners isn't enough. Our first cube printed its start line fine on the left, but the first layer didn't stick in the middle: the nozzle was 0.3 mm too high there. The middle of an Ender bed is often lower than the corners, and we had also moved the magnetic sheet after levelling. Use Klipper's paper test at the centre:

1. Bed at 60°C, then `G28` and `G1 X117.5 Y117.5 Z5`.
2. `Z_ENDSTOP_CALIBRATE`, then `TESTZ Z=-4.5` to bring the nozzle down to 0.5 mm.
3. With the paper under the nozzle, step down with `TESTZ Z=-0.1`, then `TESTZ Z=-0.025` near the end, until the paper drags slightly.
4. `ACCEPT`, then `SAVE_CONFIG`. Klipper writes the height to the bottom of `printer.cfg` and restarts.

Ours came out at `position_endstop: -0.300`. Klipper then refused to start (`position_endstop in section 'stepper_z' must be between position_min and position_max`), because the height was below zero. Add `position_min: -2` under `[stepper_z]` and `RESTART`.

If you level the corners again later, do this again afterwards.

**Fine-tune during the first layer.** If the first layer still looks too high or too low, lower or raise the nozzle while it prints: `SET_GCODE_OFFSET Z_ADJUST=-0.05 MOVE=1` (minus = closer to the bed), or Mainsail's Z offset buttons in the Tool panel. It's lost on restart, so once it looks right, save it with `Z_OFFSET_APPLY_ENDSTOP`, then `SAVE_CONFIG`. A higher (less negative) `position_endstop` means the nozzle sits closer to the bed. Ours went from `-0.300` to `-0.250`, then `-0.150`, then `-0.100`, then `-0.050` after cleaning the bed and nozzle properly (the key cover brim still started too high before that). Stop and clean the bed between tries; a failed first layer left on the bed spoils the next one.

Then the first print:

1. **Line test.** Print the two-line test file (ours was sliced in Cura with the bed at 35°C; note that a print waits for the bed to **cool** to its temperature too, so if you've just levelled at 50°C it sits still for a few minutes first): it draws two lines along the left edge of the bed. The lines should be flat and slightly squashed, not round (nozzle too high) or see-through and scraped (too low). Re-level if not.
   If nothing comes out, the filament probably hasn't reached the nozzle yet: the test lines only push about 30 mm, which can all go into filling an empty hot end. Load it first: heat the nozzle (`M109 S200`), then push 50 mm slowly with the nozzle in the air (`G91`, `G1 E50 F120`, `G90`) until plastic comes out of the tip. That's what happened to us.
   The tube from the extruder to the nozzle is about 40 cm long, so a fresh filament needs about 400 mm fed before plastic comes out. Feed it fast while it's in the tube (`G1 E50 F600`, repeated; Klipper refuses more than 100 mm in one move), then slowly for the last few cm.

   **Loading by hand** is quicker: heat the nozzle to 200°C, squeeze the spring lever on the extruder (the black box on the frame) to open the gear, and push the filament through the tube until plastic comes out of the nozzle. Mainsail's **Extrude** button in the Tool panel does the same as the `G1 E` commands.

   Plastic of a different colour coming out first is old filament left in the nozzle. Keep feeding until the new colour runs clean. Ours came out black before the green.

   **The printer can't see the filament.** The stock Ender 3 Pro has no filament sensor. We tried watching the nozzle temperature: as the cold filament reached the hot zone, the temperature dipped by 0.5°C and the heater power rose from 48% to 57%, then settled again. It's a real signal, but small, so check with your eyes.
2. **Test cube.** Slice a 20 mm calibration cube in Cura (see _Slicing in Cura_ below), upload it in Mainsail and print.

### Slicing in Cura

1. **Printer:** Creality Ender-3 Pro. Its start G-code works with Klipper unchanged.
2. **Material:** Generic PLA.
3. **Print settings → Custom**, search for and set:

| Setting | Value |
| --- | --- |
| Printing Temperature | 200 |
| Build Plate Temperature | 60 |
| Layer Height | 0.2 |
| Build Plate Adhesion Type | Skirt |

4. **Check a model is on the plate** and Cura shows layers and a print time. Our first test file had no model in it (`;LAYER_COUNT:0`, empty `MINX`/`MAXX`), so it only drew Cura's two start lines.
5. **Slice**, **Save to Disk**, then upload on Mainsail's **G-Code Files** page. Cura's Marketplace plugin "Moonraker Connection" can send files straight to the printer instead.

**Slicing without the Cura app.** Cura ships its engine as a command-line program (`/Applications/UltiMaker Cura.app/Contents/Frameworks/CuraEngine`). We sliced with it using the Ender-3 Pro definition and `-s` settings (bed 60, nozzle 200, layer 0.2, skirt). Two settings had to be given by hand, or it stopped with `no value given`: `flooring_layer_count=0` and `roofing_layer_count=0`. Leave `mesh_position_x/y` out, because the engine centres the model by itself. It does **not** drop the model onto the bed: anything below Z 0 in the STL is cut off. Our key cover's STL started at Z −7.2, and the first slice came out 12.8 mm tall instead of 20. Move the model to Z 0 first (with `trimesh`: `m.apply_translation(-m.bounds[0])`), and check `;MAXZ` in the G-code matches the model's height. The Cura app does this for you.

**Turning a model to lie flat.** Python with `trimesh` can rotate an STL (we turned a key cover from standing on edge to lying flat: 90° about X, then moved onto the bed). A hollow part lying flat has to bridge its gap in mid-air, so slice with `bridge_settings_enabled=true`.

Use the same bed temperature you levelled at. A file with a cooler bed waits for the bed to cool before it starts.

## Changing a model: OpenSCAD in Docker

Many Thingiverse models come with an OpenSCAD source file (`.scad`) next to the STL. Its settings (text, sizes) are plain variables at the top, so a new version is one command away, without sculpting anything.

The OpenSCAD app can't be installed with Homebrew any more: `brew install --cask openscad` says it's disabled because it fails Apple's Gatekeeper check. Use the official Docker image instead. In the folder with the `.scad` file:

```
docker run --rm -v "$PWD":/w -w /w openscad/openscad:latest \
  openscad -o Keycap_Car.stl -D 'text="Car"' -D 'textdepth=0.6' keycap_doublesided_text.scad
```

Each `-D` overrides one variable from the top of the `.scad` file. The STL comes out wherever the model sits in OpenSCAD, often partly below Z 0, so move it onto the bed before slicing (see _Slicing without the Cura app_, in Step 9).

**Our four key covers** (labels F1, F2, B, U):

```
for t in F1 F2 B U; do
  docker run --rm -v "$PWD":/w -w /w openscad/openscad:latest \
    openscad -o "Keycap_$t.stl" -D "text=\"$t\"" -D 'textdepth=0.6' -D 'textsize=8' \
      -D 'keydiam=24.3' -D 'keythickness=2.8' keycap_doublesided_text.scad
done
```

1. **Fit the key first.** Measure the key's round head. The model is made for 24 mm across and 2.5 mm thick; ours was 24 × 2.5 mm (measure carefully: we first guessed 4, then 3). A printed slot comes out slightly tight, so add 0.3 mm to both: `keydiam=24.3`, `keythickness=2.8`.
1. **Text depth.** The original is `-0.1` (cut in 0.1 mm), too faint to read on a print. Cutting deeper isn't safe: the wall is only 0.8 mm, and 0.6 mm in would nearly break through to the key slot. Positive values make the text stand out instead, so we used `textdepth=0.6`.
2. **Text size.** `textsize=8` instead of 5, since one or two letters leave plenty of room.
3. **One plate.** We put all four on one plate with `trimesh`: each moved onto the bed, then side by side, then `trimesh.util.concatenate`. Spaced 22 mm apart; one print, about 40 minutes, 1.6 m of filament, with a 5 mm brim each.

**Which way up.** Keep the designer's orientation unless there's a reason not to. We tried laying our key cover flat, but it's hollow: the top would have to span 24 mm in mid-air and could sag into the key slot, and the 0.1 mm text on the underside would vanish into the first layer. Standing on its flat edge, with a 5 mm brim for grip, it prints clean.

## If prints stop with "Timer too close"

Our first real print stopped while homing with `MCU 'mcu' shutdown: Timer too close`. The Pi Model B was too busy to send the moves on time. `top` showed the kernel's memory reclaimer, `kswapd0`, at 43% CPU: the Pi had only 173 MB of its 256 MB, because the rest was reserved for graphics. Power and heat were fine (`vcgencmd get_throttled` = `0x0`, 34°C).

Two fixes:

1. Give graphics the minimum. Add `gpu_mem=16` to the end of `/boot/firmware/config.txt` and reboot. Ours went from 173 MB to 221 MB.
2. Put Klipper ahead of everything else. Create `/etc/systemd/system/klipper.service.d/priority.conf`, then `sudo systemctl daemon-reload` and restart Klipper:

    ```
    [Service]
    Nice=-15
    IOSchedulingClass=realtime
    ```

Also close Mainsail tabs you're not watching during a print. Each open tab costs the Pi work.

After the shutdown, the printer's board stays in its safety stop even through a Pi reboot, because USB keeps it powered. Run FIRMWARE RESTART.

A Pi 2 or newer avoids all of this. Pi OS 32-bit runs on every model, so the same card moves across unchanged.

## If the Pi crashes or loses power

Our Pi crashed or lost power several times during the install. It rebooted on its own once, and once it would only show the red light. Each time, a file that was being written got lost without any error:

1. On the next boot, ext4 runs "orphan cleanup", which **deletes files that were being written at the moment of the crash**.
2. apt still lists them as installed, so nothing warns you.
3. We lost: the Wi-Fi drivers (`.../drivers/net/wireless/ralink/rt2x00/`), the `zram` module, some Perl files used by apt, and the Python package `markupsafe` in `~/moonraker-env`.

What to do after a crash:

1. Find packages with missing files: `sudo dpkg --verify 2>/dev/null | grep -v " c "`, then `sudo apt-get install --reinstall <package>` for each one listed.
2. Moonraker won't start (`Failed to load 'template' component` in `~/printer_data/logs/moonraker.log`): reinstall its Python packages. The `klippy_uds_address` named in that error is a red herring; the real error underneath is `No module named 'markupsafe'`.

   ```
   ~/moonraker-env/bin/pip install --force-reinstall -r ~/moonraker/scripts/moonraker-requirements.txt
   sudo systemctl restart moonraker
   ```
3. Turn on the persistent journal, so the logs from before a crash survive: `sudo mkdir -p /var/log/journal && sudo systemctl restart systemd-journald`. Read them with `sudo journalctl -b -1`.

To avoid crashes: use a proper 5V 2.5A supply, and always run `sudo shutdown now` and wait for the green light to stop before unplugging. `vcgencmd get_throttled` read `0x0` for us, so we never proved the cause. Suspects are the power supply, the SD card or the card slot.

If it keeps crashing, rewrite the card (Step 1) and reinstall (Steps 3–5, 8). The printer's firmware doesn't need flashing again. Or use the UTM virtual machine below.

## Checking the Pi without SSH

Moonraker's web API answers anything on the home network, no password needed. From the Mac:

| Command | Shows |
| --- | --- |
| `curl -s http://ender.local/printer/info` | Klipper state (`ready`, `startup`, `error`), the error message, and the Klipper version |
| `curl -s http://ender.local/machine/peripherals/usb` | USB devices on the Pi. The printer is `1a86 7523 CH340 serial converter`. If it's missing, it's the cable |
| `curl -s http://ender.local/machine/peripherals/serial` | Serial ports, with the `/dev/serial/by-id/...` path for `printer.cfg` |
| `curl -s http://ender.local/server/files/klippy.log \| tail -30` | The end of Klipper's log |
| `curl -s http://ender.local/server/files/config/printer.cfg` | The current `printer.cfg` |
| `curl -s -X POST http://ender.local/printer/firmware_restart` | Same as the FIRMWARE RESTART button |

If you can't remember the Pi's address, run `arp -a` on the Mac. A Pi's MAC address starts with `b8:27:eb`.

## No Pi? Run it in a UTM virtual machine on the Mac

A fallback if the Pi stops working: our Pi went quiet once after flashing and came back later. Docker can't do this, because Docker on a Mac has no USB passthrough. A UTM virtual machine can.

The Mac must stay **awake for the whole print**. If it sleeps or restarts, the print stops.

**Create the VM**

1. Install UTM, free from [mac.getutm.app](https://mac.getutm.app).
2. Download the Debian 13 **arm64 netinst** ISO from [cdimage.debian.org](https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/).
3. In UTM: **Create a New Virtual Machine → Virtualize → Linux**.
4. Leave **Use Apple Virtualization off**. USB passthrough only works with QEMU.
5. Boot ISO: the Debian file. Memory **2048 MB**, CPU **2 cores**, disk **16 GB**. Name it `ender`.
6. Before starting it, open its settings:
   1. **Network → Bridged (Advanced)**, interface `en0`. The VM gets an address on your home network, like the Pi did.
   2. **Input → USB Sharing** on, USB 3.0 controller.

**Install Debian**

7. Start the VM and choose **Install** (text mode is fine).
8. Hostname `ender`. Leave the **root password blank**, so your user gets `sudo`. User `admin`.
9. Software selection: only **SSH server** and **standard system utilities**. No desktop.
10. When it finishes, clear the CD/DVD drive in UTM and restart the VM.
11. Log in on the VM screen and run `sudo apt install -y avahi-daemon`, so `ender.local` works.
12. From the Mac Terminal: `ssh-copy-id admin@ender.local`

**Install Klipper, Moonraker and Mainsail**

13. Follow Steps 3, 4 and 5 exactly as written. Skip the swap file, which the VM doesn't need. It installs in minutes, not an hour.

**Connect the printer**

14. Plug the printer's USB into the Mac and switch the printer on.
15. In the UTM window toolbar, click the **USB icon** and pick **USB Serial** (CH340, `1a86:7523`). It disconnects from the Mac and appears in the VM.
16. Check with `ls /dev/serial/by-id/` in the VM. The port name is the same as on the Pi, so `printer.cfg` from Step 8 works unchanged.
17. Open `http://ender.local` on the Mac.

**Every time you print**

18. Start UTM and the `ender` VM, then reconnect the USB device (step 15).
19. Keep the Mac awake: run `caffeinate -dimsu` in a Terminal for the length of the print, and Ctrl+C when it's done.

The printer's firmware stays as it is. You only rebuild it (Step 6) when you update Klipper, using the VM's version: `ssh admin@ender.local 'git -C ~/klipper rev-parse HEAD'`.

## Problems we hit and fixes

| Problem | Cause | Fix |
| --- | --- | --- |
| Desktop version stuck on first boot for a long time | Full Raspberry Pi OS is too heavy for an old Pi | Use Raspberry Pi OS Lite |
| "Welcome to the Raspberry Pi desktop" setup screen | Imager settings weren't applied | Fill in every customisation setting before writing |
| `systemd-rfkill.service` repeating at boot | USB Wi-Fi dongle hanging the boot | Unplug the dongle and use Ethernet |
| Stuck on "job NetworkManager.service/start running" | Same Wi-Fi dongle problem | Unplug the dongle and use Ethernet |
| Pi not found on the network | Wi-Fi never connected | Ethernet cable, then `ping ender.local` |
| SSH "connection refused" | SSH not switched on yet | Wait a minute, or turn it on in `raspi-config` |
| SSH "permission denied (publickey)" | Mac's key not on the Pi | `ssh-copy-id admin@ender.local` |
| Pi much slower than expected | It was a Model B Rev 1, not a Pi 2 | Check the model; plan a Pi 3 or Zero 2 W |
| Printer files lost | Imager erased the card | Copy files off the card first |
| Install would take hours | Klipper's script installs ARM compilers | Build the firmware on the Mac with Docker |
| `mcu 'mcu': Unable to connect` | Charge-only USB cable: no printer in the Pi's USB list | Use a data cable |
| `No communication with MCU` after the new cable | The bootloader flashed a Pi file (`cmdline.txt`, `ISSUE.TXT`) instead of Klipper. It takes the first file on the card | Card with only the firmware on it (Step 7) |
| Switching the printer off and on didn't reflash it | The board stays powered over USB from the Pi or Mac | Unplug the USB cable, then switch on |
| SSH to the Pi "permission denied" | Tried the users `pi`, `mainsail` and `klipper` | The user is `admin` |
| `brew install gcc-arm-embedded` failed | The installer needs the Mac password (sudo) | Build in Docker instead (Step 6) |
| Firmware built from the wrong Klipper version | Built from the latest Klipper, not the Pi's | Read the Pi's version from `/printer/info`, build from that commit |
| Printer screen blank after flashing | Normal with Klipper. It's also blank when the flash failed, so it tells you nothing | Check Mainsail or the bootloader messages (Step 7) |
| Bootloader loops `Update failed, No SD/TF-Card or error` | No working firmware on the board, and no card, or a card it can't use | Flash again with only the firmware on the card |
| Bootloader says `read file name : ISSUE.TXT` | It flashes the first file on the card | Only the firmware on the card |
| Hidden `._fw-....bin` file on the card | macOS writes it when copying | `cp -X`, then `dot_clean -m /Volumes/<card>` |
| Recording the bootloader with `cat` gave gibberish | macOS reset the port speed | Record with pyserial at 115200 |
| Read `12864ZW-10` and thought it was the board | That's the display's board, behind the screen | The main board is in the box under the screen |
| No `wlan0` although `lsusb` shows the dongle | Driver files deleted by a crash | Reinstall the kernel package (_Wi-Fi with a USB dongle_) |
| Wi-Fi drops after about 20 seconds | Dongle can't wake from power-save | `wifi.powersave = 2` |
| Dongle vanishes from `lsusb`, error -71 | Not enough USB power | Other USB port |
| Moonraker: `Failed to load 'template' component` | `markupsafe` deleted by a crash | Reinstall Moonraker's Python packages |
| `Timer too close` right after boot | Single-core Pi busy while booting | FIRMWARE RESTART; for good, the boot delay in Step 8 |
| Line test ran but nothing came out of the nozzle | Filament hadn't reached the nozzle yet; the test only pushes about 30 mm | Load it first: heat to 200°C, `G91` + `G1 E50 F120` + `G90`, until plastic comes out |
| Print stops while homing: `MCU 'mcu' shutdown: Timer too close` | Pi Model B out of memory (`kswapd0` busy) | `gpu_mem=16`, Klipper priority (_If prints stop with "Timer too close"_), or a Pi 2 or newer |
| First layer of the cube didn't stick in the middle, but the start line did | Nozzle 0.3 mm too high in the middle | Paper test at the centre with `Z_ENDSTOP_CALIBRATE` (Step 9) |
| `position_endstop in section 'stepper_z' must be between position_min and position_max` after `SAVE_CONFIG` | Saved height is below 0 | `position_min: -2` under `[stepper_z]` |
| First layer still "not sticking" after lowering the nozzle again and again | Leftover cold plastic on the bed or a blob on the nozzle catches the new lines and drags them off | Clean the nozzle tip and every scrap off the bed before each try; don't keep lowering |
| `Must home axis first` when trying to raise the head after a print | The print's end switches the motors off, so Klipper forgets where the axes are. `SET_KINEMATIC_POSITION` didn't help on our version | `G28`, then `G1 Z60` |
| Print started but nothing moves, nozzle hot | The bed is above the file's bed temperature (35°C after levelling at 50°C), and Klipper waits for it to cool | Wait, or slice with the bed at the levelling temperature (60°C for PLA) |
| Mainsail: `gcode_macro pause is not defined in config` | Mainsail's macros not installed | `[include mainsail.cfg]` (Step 8) |

## Moving the SD card to a faster Pi (Raspberry Pi 3 Model B)

Done 2026-11-09. The same SD card booted on a Pi 3 Model B Rev 1.2 with no changes: Raspberry Pi OS ships kernels for every model (`rpi-v6`, `rpi-v7`, `rpi-v8`) and picks the right one at boot.

What was checked after the move:

1. `cat /proc/device-tree/model` gives `Raspberry Pi 3 Model B Rev 1.2`. 4 cores at 1200 MHz, 1 GB RAM (the old Model B had 1 core and 256 MB).
2. Kernel `6.18.50+rpt-rpi-v7`, hostname, IP (`192.168.0.241`), Klipper drop-ins (`Nice=-15`, `wait-for-printer.conf`), Moonraker and nginx all carried over.
3. Wi-Fi: the Pi 3's built-in Wi-Fi (`wlan0`, driver `brcmfmac`) joined the saved network by itself. The USB dongle shows as `wlan1` and is not used, so it can be unplugged.
4. Swap: the 1 GB `/swapfile` plus 1 GB zram. With 1 GB of RAM it is rarely touched.
5. Power: `vcgencmd get_throttled` read `0x50005` and `dmesg` showed `Undervoltage detected!` within 2 minutes of boot. The Pi 3 needs a 5V 2.5A supply and a short, thick cable. Under-voltage slows the CPU down and can corrupt the SD card (see "files went missing after crashes").

How to read `get_throttled`: bit 0 = under-voltage now, bit 2 = throttled now, bit 16 = under-voltage has happened since boot, bit 18 = throttled since boot. `0x0` is the only good value.

Tweaks made on the Pi 3:

1. `wait-for-printer.conf`: the settle wait after the printer appears went from `sleep 30` to `sleep 10`. The old Pi needed 30s; the Pi 3 doesn't.
   `sudo sed -i "s/sleep 30/sleep 10/" /etc/systemd/system/klipper.service.d/wait-for-printer.conf && sudo systemctl daemon-reload`
2. Turned off services a print server doesn't need:
   `sudo systemctl disable --now bluetooth.service packagekit.service && sudo systemctl mask packagekit.service`
   (packagekit is masked because apt can wake it up again.)
3. Not done on purpose: no overclock and no governor change. The Pi 3 already runs at 1200 MHz, and with 1 GB of RAM it doesn't run short of memory. Overclocking while it is under-voltage would make crashes more likely.

### Letters cut into the surface instead of raised

1. A negative `textdepth` cuts the text into the face instead of raising it.
2. The default `wall=0.8` is too thin for that: a 0.6 mm cut leaves 0.2 mm, less than one 0.4 mm nozzle line, so the slicer drops it and the letters become holes through to the key. Raise the wall with the cut:
   ```
   docker run --rm -v "$PWD":/w -w /w openscad/openscad:latest openscad -o "Keycap_${t}_engraved.stl" -D "text=\"$t\"" -D 'textdepth=-0.6' -D 'wall=1.2' -D 'textsize=8' -D 'keydiam=24.3' -D 'keythickness=2.8' keycap_doublesided_text.scad
   ```
   This leaves 0.6 mm under each letter, and the cover is 5.2 mm thick (the raised version is 5.6 mm).
3. Preview a model with OpenSCAD's own renderer (it shows cut-in detail much better than a matplotlib plot). Make a file holding `import("X.stl");` and run:
   ```
   docker run --rm -v "$PWD":/w -w /w openscad/openscad:latest sh -c "xvfb-run -a openscad -o face.png --imgsize=500,500 --viewall --autocenter --camera=0,0,0,70,0,25,0 --colorscheme=Tomorrow view.scad"
   ```

### Nozzle height after the move to the Pi 3 (2026-11-09)

The first cut-in F1 did not stick at `position_endstop: -0.050`. Lowered the nozzle 0.05 mm and saved it in one go:

```
SET_GCODE_OFFSET Z_ADJUST=-0.05
Z_OFFSET_APPLY_ENDSTOP
SAVE_CONFIG
```

Saved value now `position_endstop: 0.000`. On the Pi 3, Klipper was ready again 20 seconds after `SAVE_CONFIG`.

### Shorter cover, letters cut right through (v3, 2026-11-09)

The 20.9 mm cover was too hard to push onto the key: the open bottom edge is a chord of the 24.3 mm slot, only 19.1 mm wide. A copy of the `.scad`, `keycap_v3.scad`, adds three settings:

1. `opening`: distance from the centre to the open bottom edge. The original is 7.5 mm. `opening=4.5` removes 3 mm, so the cover is 17.9 mm tall and the entry is 22.6 mm wide (chord width = 2 × √(r² − opening²), with r = 12.15).
2. `bridges` and `bridgew`: thin vertical strips left in letters that have closed holes (B, O, A, 8...). Without them, cutting the letter right through makes the inside parts fall out. For B in the default font at size 6, the strip goes at `x=0` (through the middle) or `x=-0.95` (next to the upright). Measure a letter's holes by exporting it as SVG (`openscad -o b.svg` with just the `text()` call) and reading the path bounds.
3. `textdepth=-1.3` with `wall=1.2` cuts right through the wall, so the key shows through the letters. `textsize=6` and `textoffset=0.8` keep the letters between the ring hole and the new bottom edge.

```
docker run --rm -v "$PWD":/w -w /w openscad/openscad:latest openscad -o Keycap_B_v3.stl -D 'text="B"' -D 'bridges=[0]' -D 'textdepth=-1.3' -D 'wall=1.2' -D 'textsize=6' -D 'textoffset=0.8' -D 'opening=4.5' -D 'keydiam=24.3' -D 'keythickness=2.8' keycap_v3.scad
```

Cutting the letters right through was dropped (the bridges made B read like "E3" or "13"). Final v3: letters cut 0.6 mm in, as before, on the shorter cover. `textdepth=-0.6`, everything else as above, no `bridges`.

### Prints end as "cancelled" and the head doesn't move away

Symptom: the last layer or two are missing, the head stays on top of the model, Mainsail shows the print as cancelled, and the console says `Extrude below minimum temp` / `"extruder" not hot enough`.

Cause: the CuraEngine command-line slice lowers the nozzle temperature over the last layers (`M104 S194.9`, `S167`, `S136.6` ... `S0.8`). Klipper won't extrude below `min_extrude_temp` (170°C), so it aborts the print, and the end G-code that lifts the head and pushes the bed forward (`G1 X0 Y220 ;Present print`) never runs. Setting `material_final_print_temperature`, `machine_nozzle_cool_down_speed` or `machine_min_cool_heat_time_window` on the command line did not stop it.

Fix: after slicing, remove every `M104` between `;LAYER:0` and the end G-code with a small script, `nocooldown.py`:

```python
import re, sys
for path in sys.argv[1:]:
    out, inprint = [], False
    for line in open(path):
        if line.startswith(";LAYER:0"):
            inprint = True
        elif inprint and line.startswith("M140 S0"):
            inprint = False
        if inprint and re.match(r"M104 S", line):
            continue
        out.append(line)
    open(path, "w").writelines(out)
```

Run it with `python3 nocooldown.py file.gcode`, then check with `grep "^M104" file.gcode`. Only the start heat-up and the `S0` turn-off lines should be left.

### Unloading filament (run out mid-print)

1. If the print was stopped with Mainsail's emergency stop, Klipper shows `Shutdown due to webhooks request` and nothing runs until `FIRMWARE_RESTART`. The print can't be resumed after that. Use PAUSE instead if you want to resume.
2. Heat, push 5 mm to soften the tip, then pull back about 450 mm in steps of 90 (Klipper refuses single extrude-only moves over `max_extrude_only_distance: 100`):
   ```
   M109 S200
   M83
   G1 E5 F300
   G1 E-90 F1800   ; five times
   M400
   M104 S0
   ```
3. `M109` waits for the heat, so a call through `/printer/gcode/script` can time out at nginx (504) while Klipper keeps going. The next commands still queue behind it.
4. `G28` then `G1 Z30` puts the head home and raised, ready for loading. `M84` with any argument still turns off every motor in Klipper, so homing is lost. Home again before moving.
