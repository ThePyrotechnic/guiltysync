"""
guiltysync - Sync Guilty Gear Strive mods
    Copyright (C) 2023  Michael Manis - michaelmanis@tutanota.com
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.
    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from collections import defaultdict
import json
from pathlib import Path
import shutil
import webbrowser

import click
import requests
from requests import HTTPError, ConnectionError

import guiltysync
from guiltysync.scripts.server import server 


def print_mods(mods):
    click.echo("Your mods:")
    [click.echo(f"\t{data['name']}") for data in mods.values()]


def check_server(server):
    requests.get(server).raise_for_status()


def create_group(server, group_name, nickname, mods):
    res = requests.post(f"{server}/groups/{group_name}",
        json={
            "member": nickname,
            "mods": {data["id"]: {"name": data["name"], "id": data["id"]} for data in mods.values() if data["external"] is False}
        }
    )
    res.raise_for_status()


def update_user(server, group_config, mods):
    res = requests.put(f"{server}/groups/{group_config['name']}/{group_config['nickname']}",
        json={
            "member": group_config["nickname"],
            "mods": {data["id"]: {"name": data["name"], "id": data["id"]} for data in mods.values() if data["external"] is False}
        }
    )
    res.raise_for_status()


def print_list_options(l):
    for index, item in enumerate(l, 1):
        click.echo(f"{index}:\t {item}")


def write_config(path, config_data):
    with open(path, "w", encoding="UTF-8") as client_config_file:
        json.dump(config_data, client_config_file)


def launch_game():
    webbrowser.open("steam://run/1384160")


def prompt_launch(success = False):
    if click.confirm(f"Do you want to launch the game{'' if success else ' anyway'}?"):
        launch_game()
        exit(0)
    return False


def scan_mods(game_dir, shared_dir):
    mods = defaultdict(dict)

    for file_ in shared_dir.glob("**/*"):
        if file_.suffix == ".pak":
            mods[file_.stem]["name"] = file_.stem
            mods[file_.stem]["parent_dir"] = file_.parent
            mods[file_.stem]["external"] = file_.parts[-3] == "external"
            mods[file_.stem]["pak"] = file_
        elif file_.suffix == ".sig":
            mods[file_.stem]["sig"] = file_
        elif file_.suffix == ".id":
            # Need to chop off ID suffix (pathlib does not do this)
            # [1:] gets rid of leading period character in ID
            # Don't want to split entire filename because mod name may have a period in it
            filename, id_, _ = file_.name.rsplit(".", maxsplit=2)
            mods[filename]["id"] = id_

    invalid_mods = []
    for mod_name, mod_info in mods.items():
        required_keys = ["pak", "sig", "id"]
        for key in required_keys:
            if not mod_info.get(key):
                if key == "sig":  # Try to fix missing .sig
                    relative_sig_filepath = mods[mod_name]["parent_dir"] / Path(f"{mod_name}.sig")
                    sig_filepath = shared_dir / relative_sig_filepath
                    game_sig_filepath = game_dir / Path("RED", "Content", "Paks", "pakchunk0-WindowsNoEditor.sig")
                    shutil.copy(game_sig_filepath, sig_filepath)
                    mod_info["key"] = relative_sig_filepath
                else:
                    click.echo(f"WARNING: Mod '{mod_name}' is missing '{key}' file. Skipping mod")
                    invalid_mods.append(mod_name)
                    break
    for invalid_mod in invalid_mods:
        del mods[invalid_mod]
    
    # Very lazy method of doing this (could integrate into first scan)
    mods_by_id = {}
    for mod_name, mod_info in mods.items():
        mods_by_id[mod_info["id"]] = mod_info

    return mods_by_id


def show_group_info(client_config, mods, group_name, group_data):
    to_be_downloaded = {}
    to_be_removed = {mod_id: mod_data for mod_id, mod_data in mods.items() if mod_data["external"]}
    click.echo("Current group data:")
    for user, their_mods in group_data.items():
        if user == client_config["groups"][group_name]["nickname"]:
            continue
        click.echo(f"{user}:")
        for mod_id, mod_data in their_mods.items():
            if mod_id in mods:
                try:
                    del to_be_removed[mod_id]
                except KeyError:
                    pass
                status = "✅[HAVE]"
            else:
                status = "🔄[NEED]"
                to_be_downloaded[mod_id] = mod_data

            click.echo(f"\t{status} {mod_data['mod_name']}")

    click.echo(f"{client_config['groups'][group_name]['nickname']}:")
    for mod_id, mod_data in mods.items():
        if mod_id in to_be_removed.keys():
            click.echo(f"\t❌[DELETE] {mod_data['name']}")
        else:
            click.echo(f"\t✅[HAVE] {mod_data['name']}")

    return to_be_downloaded, to_be_removed


def handle_mods(server, game_dir, shared_dir, client_config, mods, group_config):
    group_data = requests.get(f"{server}/groups/{group_config['name']}").json()

    to_be_downloaded, to_be_removed = show_group_info(client_config, mods, group_config['name'], group_data)
    
    click.echo()
    changes_required = False
    if len(to_be_downloaded) > 0:
        changes_required = True
        click.echo("The following mods will be downloaded")
        for mod_data in to_be_downloaded.values():
            click.echo(f"\t🔄[NEED] {mod_data['name']}")

    if len(to_be_removed) > 0:
        changes_required = True
        click.echo("The following mods will be deleted")
        for mod_data in to_be_removed.values():
            click.echo(f"\t{mod_data['name']}")

    if changes_required:
        if not click.confirm("Is this okay?") and not prompt_launch():
            click.echo("Quitting...")
            exit(1)

    for mod_data in to_be_downloaded.values():
        click.echo(f"Downloading {mod_data['name']}...")
        current_mod_dir = shared_dir / Path("external", mod_data["id"])
        current_mod_dir.mkdir(parents=True, exist_ok=True)
        try:
            guiltysync.download_mod(current_mod_dir, mod_data["id"])
        except click.ClickException as e:
            click.echo(e)
            if not click.confirm("An error occurred while downloading this mod. Do you want to skip it?") and not prompt_launch():
                click.echo("Quitting...")
                exit(1)
    
    for mod_data in to_be_removed.values():
        click.echo(f"Deleting {mod_data['name']}...")
        for file_ in mod_data["parent_dir"].glob(f"{mod_data['name']}*"):
            if file_.is_file():
                click.echo(f"\tDeleting {file_}...")
                file_.unlink()
        if len(list(mod_data["parent_dir"].glob("*"))) == 0:
            click.echo(f"\tDeleting {mod_data['parent_dir']}...")
            mod_data["parent_dir"].unlink()

    if changes_required:  # Don't print list again unless something happened
        mods = scan_mods(game_dir, shared_dir)
        show_group_info(client_config, mods, group_config['name'], group_data)
    
    return mods



@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        ctx.forward(sync)


@click.option("--game-dir", default=None)
@click.option("--server", default=None)
@cli.command()
def sync(game_dir, server):
    client_config_filepath = Path("guiltysync.json")
    if (not client_config_filepath.exists()):
        if (click.confirm("GuiltySync config was not found. Create one now?")):
            default_config = {
                "groups": {},
                "defaults": {}
            }
            client_config_filepath.write_text(json.dumps(default_config), encoding="UTF-8")
        elif not prompt_launch():
            click.echo("Quitting...")
            exit(1)

    with open(client_config_filepath, "r", encoding="UTF-8") as client_config_file:
        client_config = json.load(client_config_file)

    if game_dir is None:
        game_dir = client_config["defaults"].get("game_dir")
        if game_dir is None:
            game_dir = click.prompt("Input your game directory (The folder with GGST.exe in it)")
    game_dir = Path(game_dir)
    client_config["defaults"]["game_dir"] = game_dir.as_posix()

    if server is None:
        server = client_config["defaults"].get("server")
        if server is None:
            server = click.prompt("Input the sync server that you want to connect to")
    client_config["defaults"]["server"] = server
    
    write_config(client_config_filepath, client_config)

    mod_root = game_dir / Path("RED", "Content", "Paks")
    if (not mod_root.exists()):
        click.echo("Invalid game directory")
        if not prompt_launch():
            raise click.ClickException("Invalid game directory")

    mod_dir = mod_root / Path("~mods")    
    if (not mod_dir.exists()):
        if(click.confirm("Mod folder does not exist (~mods). Do you want to create it?")):
            mod_dir.mkdir()
        elif not prompt_launch():
            click.echo("Quitting...")
            exit(1)
    
    shared_dir = mod_dir / Path("shared")
    if (not shared_dir.exists()):
        if (click.confirm("shared folder does not exist (~mods/shared). Do you want to create it?")):
            shared_dir.mkdir()
        elif not prompt_launch():
            click.echo("Quitting...")
            exit(1)

    mods = scan_mods(game_dir, shared_dir)

    print_mods(mods)
    click.echo()

    try:
        check_server(server)
    except (HTTPError, ConnectionError) as e:
        click.echo(e)
        click.echo("Unable to reach sync server")
        if not prompt_launch():
            click.echo("Quitting...")
            raise click.ClickException("Unable to reach sync server")

    group_is_new = False
    groups = list(client_config["groups"].keys())
    if len(groups) == 0:
        group_is_new = True
        click.echo("No groups found")
        group_name = click.prompt("Enter a group name")
    else:
        groups.append("Join/create a new group...")
        while True:
            click.echo("Choose a group:")
            print_list_options(groups)
            choice = click.prompt("Choose an option", type=int) - 1
            if choice == len(groups) - 1:
                group_is_new = True
                group_name = click.prompt("Enter a group name")
                break
            try:
                group_name = groups[choice]
                break
            except ValueError:
                pass
    if group_is_new:
        nickname = click.prompt("Create a nickname for yourself in this group")
        client_config["groups"][group_name] = {"name": group_name, "nickname": nickname}
        try:
            create_group(server, group_name, nickname, mods)
        except HTTPError as e:
            if e.response.status_code == 409:
                click.echo("Found an existing group")
            else:
                click.echo(e)
                if not prompt_launch():
                    click.echo("Quitting...")
                    raise click.ClickException("An error occurred while creating a new group")
    try:
        group_config = client_config["groups"][group_name]
        update_user(server, group_config, mods)
    except HTTPError as e:
        if e.response.status_code == 404:
            del client_config["groups"][group_config["name"]]
            write_config(client_config_filepath, client_config)
        click.echo(e)
        if not prompt_launch():
            click.echo("Quitting...")
            raise click.ClickException("An error occurred while creating a new group")
        raise click.ClickException("An error occurred while adding the user to the group")

    write_config(client_config_filepath, client_config)

    mods = handle_mods(server, game_dir, shared_dir, client_config, mods, group_config)

    while True:
        print_list_options(["Refresh...", "Launch GGST", "Quit"])
        choice = click.prompt("Choose an option", type=int) - 1
        if choice == 0:
            mods = scan_mods(game_dir, shared_dir)
            update_user(server, group_config, mods)
            mods = handle_mods(server, game_dir, shared_dir, client_config, mods, group_config)
        elif choice == 1:
            launch_game()
            exit(0)
        elif choice == 2:
            exit(0)


cli.add_command(server)


if __name__ == "__main__":
    import sys
    cli(sys.argv[1:])