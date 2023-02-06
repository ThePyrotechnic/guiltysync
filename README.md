# GuiltySync

Sync Guilty Gear Strive mods between friends

## Installation

### Windows (tested with Proton)

1. Download `guiltysync.exe` from the latest [Release](https://github.com/ThePyrotechnic/guiltysync/releases)
2. Go to your game's installation directory
    1. From Steam, right-click `GUILTY GEAR -STRIVE-` in your library and click `Properties...`
    2. Click `LOCAL FILES`
    3. Click `Browse...`
3. Rename `GGST.exe` to `strive.exe`
4. Place `guiltysync.exe` in your game directory and rename it to `GGST.exe`

# Running

## The client

If you do not have any mods and you only want to download your friends' mods, then you do not need to do anything and you can run the client. It will walk you through the initial configuration

If you have mods that you want to share, then you must move them into the correct folder. First you should run the program once to create any missing files / folders, then follow the steps below

###

1. After running guiltysync once, you will have the following folders in your game directory:

```
RED/
└─ Content/
   └─ Paks/
      └─ ~mods/
         ├─ *< any previous mod folders/files >*
         └─ shared/
            └─ .external/
```
guiltysync will only share mods that you place inside the `~/mods/shared/` folder. The `~/mods/shared/.external/` folder is used by guiltysync to separate your friends' mods from your own, so do not place mods in that folder

2. Open your mods folder and move any mods that you want to share into the `~mods/shared/` folder. You can create nested folders if you want. Make sure that you move over the `.sig` file and the `.pak` file of each mod. If the `.sig` file is missing then guiltysync will try to create it

3. Run guiltysync and follow the instructions

## The server

No manual configuration is necessary

`guiltysync server --host <hostname> --port <port>`

The server creates a file, `config.json`, in the current directory. Be sure to port-forward whatever port you choose if you are running the server on a home connection
