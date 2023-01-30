# GuiltySync

Sync Guilty Gear Strive mods between friends

## Installation

### Windows

Grab the .exe from the latest [Release](https://github.com/ThePyrotechnic/guiltysync/releases)

### Linux / Python native

First clone the repository. Then:

```
pip install .
guiltysync <command>
```

# Running

## The client

1. If you do not have any mods and you only want to download your friends' mods, then you do not need to do anything and you can run the client. It will walk you through the initial configuration

2. If you have mods that you want to share, then you must move them into the correct folder. First you should run the program once to create any missing files / folders, then follow the simplified and/or detailed steps below (they explain the same thing)

### Simplified steps

1. For each mod you want to share, move all mod files (usually `.pak` & `.sig`) into the `~mods/shared` folder. You can create nested folders

2. Get the download ID of the mod from GameBanana by copying the download link and noting the number at the end of the url. This is *DIFFERENT* from the mod ID. ex: (for `https://gamebanana.com/dl/654361` -> `654361` is the download ID)

3. Create an empty file next to the mod's `.pak` file. Give it the _exact same_ name as the `.pak` file, but instead of `.pak` add `<ID>.id` to the end (replace `<ID>` with the download ID)

4. Run guiltysync and follow the instructions

### Detailed steps

1. After running guiltysync once, you will have the following folders in your game directory:

```
RED/
└─ Content/
   └─ Paks/
      └─ ~mods/
         ├─ *< any previous mod folders/files >*
         └─ shared/
            └─ external/
```
guiltysync will only share mods that you place inside the `~/mods/shared/` folder. The `~/mods/shared/external/` folder is used by guiltysync to separate your friends' mods from your own, so do not place mods in that folder

2. Open your mods folder and move any mods that you want to share into the `~mods/shared/` folder. You can create nested folders if you want. Make sure that you move over the `.sig` file and the `.pak` file of each mod. If the `.sig` file is missing then guiltysync will try to create it

3. For each mod that you moved over, find that mod on GameBanana and note the ID of the download. This is *DIFFERENT* from the mod ID. For example, if I wanted to share the [Maskless Jack-O mod](https://gamebanana.com/mods/318321), I would:
    1. Go to the mod page
    2. scroll to the `Files` section of the page
    3. Right-click the "Download" button for the file that I downloaded and select `Copy Link`
    4. Paste the link somewhere and note the number at the end of the link
For the Maskless Jack-O mod, the download link looks like `https://gamebanana.com/dl/654361` so the ID is `654361`

4. Now that you have the download ID, make a new empty file in the same folder where the mods `.pak` is located. Name that file the _exact same_ name as the `.pak` file, but instead of `.pak` add `<ID>.id` to the end (replace `<ID>` with the download ID)
    - For the Maskless Jack-O mod, the `.pak` file is named `Maskless Jack-O v1.2.pak`
    - I must create a new file named `Maskless Jack-O v1.2.654361.id` in the same folder as the `.pak`

5. Run guiltysync and follow the instructions

## The server

No manual configuration is necessary

`guiltysync server --host <hostname> --port <port>`

The server creates a file, `config.json`, in the current directory. Be sure to port-forward whatever port you choose if you are running the server on a home connection
