from collections import defaultdict
import json
from pathlib import Path

import click
import requests
from requests import HTTPError

import guiltysync
from guiltysync.scripts.server import server 


def print_mods(mods):
    click.echo("Your mods:")
    [click.echo(f"\t{key}") for key in mods.keys()]


def check_server(server):
    try:
        requests.get(server).raise_for_status()
    except HTTPError:
        raise ClickException("Unable to reach sync server")


def print_list_options(l):
    for index, item in enumerate(l, 1):
        click.echo(f"{index}:\t {item}")


def write_config(path, config_data):
    with open(path, "w", encoding="UTF-8") as client_config_file:
        json.dump(config_data, client_config_file)


@click.option("--dir")
@click.group()
@click.pass_context
def cli(ctx, dir):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    ctx.obj["DIR"] = dir


@click.argument("server")
@click.option("--group", "-g")
@cli.command()
@click.pass_context
def sync(ctx, server, group):
    game_dir = Path(ctx.obj["DIR"])
    
    mod_root = game_dir / Path("RED", "Content", "Paks")
    if (not mod_root.exists()):
        raise click.ClickException("Invalid game directory")

    mod_dir = mod_root / Path("~mods")    
    if (not mod_dir.exists()):
        if(click.confirm("Mod folder does not exist (~mods). Do you want to create it?")):
            mod_dir.mkdir()
        else:
            click.echo("Quitting...")
            ctx.exit(1)
    
    shared_dir = mod_dir / Path("shared")
    if (not shared_dir.exists()):
        if (click.confirm("shared folder does not exist (~mods/shared). Do you want to create it?")):
            shared_dir.mkdir()
        else:
            click.echo("Quitting...")
            ctx.exit(1)

    mods = defaultdict(dict)

    for file_ in shared_dir.glob("**/*"):
        if file_.suffix == ".pak":
            mods[file_.stem]["pak"] = file_
        elif file_.suffix == ".sig":
            mods[file_.stem]["sig"] = file_
        elif file_.suffix == ".id":
            # Need to chop off ID suffix (pathlib does not do this)
            # [1:] gets rid of leading period character in ID
            # Don't want to split entire filename because mod name may have a period in it
            mods[file_.stem.split(".")[0]]["id"] = file_.suffixes[0][1:]

    for mod, mod_info in mods.items():
        required_keys = ["pak", "sig", "id"]
        keys_found = True
        for key in required_keys:
            if not mod_info.get(key):
                click.echo(f"WARNING: Mod '{mod}' is missing '{key}' file. Skipping mod")
                keys_found = False
                break
        if not keys_found:
            continue

    print_mods(mods)
    click.echo()

    check_server(server)

    client_config_filepath = shared_dir / Path("guiltysync.json")
    if (not client_config_filepath.exists()):
        if (click.confirm("GuiltySync config was not found. Create one now?")):
            default_config = {
                "groups": {}
            }
            client_config_filepath.write_text(json.dumps(default_config), encoding="UTF-8")

    with open(client_config_filepath, "r", encoding="UTF-8") as client_config_file:
        client_config = json.load(client_config_file)

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
            choice = click.prompt("Choose an option", type=int)
            choice -= 1
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
            res = requests.post(f"{server}/groups/{group_name}",
                json={
                    "member": nickname,
                    "mods": {mod_name: {"name": mod_name, "id": data["id"]} for mod_name, data in mods.items()}
                }
            )
            res.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 409:
                click.echo("Found an existing group")
            else:
                click.echo(e)
                raise click.ClickException("An error occurred while creating a new group")
    try:
        group_config = client_config["groups"][group_name]
        res = requests.put(f"{server}/groups/{group_config['name']}/{group_config['nickname']}",
            json={
                "member": group_config["nickname"],
                "mods": {mod_name: {"name": mod_name, "id": data["id"]} for mod_name, data in mods.items()}
            }
        )
        res.raise_for_status()
    except HTTPError as e:
        if e.response.status_code == 404:
            del client_config["groups"][group_config["name"]]
            write_config(client_config_filepath, client_config)
        click.echo(e)
        raise click.ClickException("An error occurred while adding the user to the group")

    write_config(client_config_filepath, client_config)

    group_data = requests.get(f"{server}/groups/{group_config['name']}").json()
    click.echo("Current group data:")
    for user, mods in group_data.items():
        click.echo(f"{user}:")
        for mod_name in mods.keys():
            have_locally = "✅" if mod_name in mods else "❌"
            click.echo(f"\t{have_locally} {mod_name}")


cli.add_command(server)


if __name__ == "__main__":
    import sys
    cli(*sys.argv)