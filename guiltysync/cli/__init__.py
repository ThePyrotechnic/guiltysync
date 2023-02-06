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
import subprocess
import sys

import click
from packaging import version as versionLib
import requests

import guiltysync
import guiltysync.helpers as helpers
from guiltysync.cli.server import server


class ServerFailureError(BaseException):
    pass


class SyncClient:
    def __init__(self, version, config_path: Path, game_path, server):
        self.version = versionLib.parse(version)
        self.config_filepath = config_path.resolve()
        self.check_or_create_config()
        self.config = self.read_config()

        if game_path is None:
            game_path = self.config["defaults"].get("game_path")
            if game_path is None:
                game_path = Path.cwd()
        self.game_filepath = Path(game_path)
        self.config["defaults"]["game_path"] = self.game_filepath.as_posix()

        if server is None:
            server = self.config["defaults"].get("server")
            if server is None:
                while True:
                    server = click.prompt(
                        "Input the sync server that you want to connect to"
                    )
                    server = server.strip(" /")
                    if server.startswith("http"):
                        break
                    click.echo("Server address should start with 'http'")
        self.server = server
        self.config["defaults"]["server"] = server

        try:
            self.check_server()
        except requests.exceptions.RequestException:
            raise ServerFailureError()

        self.selected_group: dict = None  # type: ignore
        if self.default_group is not None:
            self.selected_group = self.groups[self.default_group]

        self.write_config()

        self.check_directories()

        self.scan_mods()

    @property
    def default_group(self):
        return self.config["defaults"].get("group")

    @default_group.setter
    def default_group(self, value):
        self.config["defaults"]["group"] = value
        self.write_config()

    @property
    def groups(self):
        return self.config["groups"]

    @groups.setter
    def groups(self, value):
        self.config["groups"] = value
        self.write_config()

    def check_directories(self):
        mod_root = self.game_filepath / Path("RED", "Content", "Paks")
        if not mod_root.exists():
            click.echo("Invalid game directory")
            if not self.prompt_launch():
                raise click.ClickException("Invalid game directory")

        mod_dir = mod_root / Path("~mods")
        if not mod_dir.exists():
            if click.confirm(
                "Mod folder does not exist (~mods). Do you want to create it?"
            ):
                mod_dir.mkdir()
            elif not self.prompt_launch():
                click.echo("Quitting...")
                sys.exit(1)

        self.shared_dir = mod_dir / Path("shared")
        if not self.shared_dir.exists():
            if click.confirm(
                "shared folder does not exist (~mods/shared). Do you want to create it?"
            ):
                self.shared_dir.mkdir()
            elif not self.prompt_launch():
                click.echo("Quitting...")
                sys.exit(1)

        self.external_dir = self.shared_dir / Path(".external")
        if not self.external_dir.exists():
            self.external_dir.mkdir()

    def check_for_update(self):
        try:
            github_res = requests.get(
                "https://api.github.com/repos/ThePyrotechnic/guiltysync/releases",
                params={"per_page": 1},
                timeout=3,
            )
            github_res.raise_for_status()
        except requests.exceptions.RequestException:
            click.echo("Failed to check for updates")
            return

        release_info = github_res.json()[0]

        release_version = versionLib.parse(release_info["tag_name"])
        if self.version < release_version:
            if sys.platform != "win32":
                click.echo(
                    f"A new version is available: {release_version} (You have {self.version})"
                )
                return

            if click.confirm(
                f"A new version is available: {release_version} (You have {self.version}). Would you like to update?"
            ):
                try:
                    dl_res = requests.get(
                        release_info["assets"][0]["url"],
                        headers={"Accept": "application/octet-stream"},
                        timeout=3,
                    )
                    dl_res.raise_for_status()
                except requests.exceptions.RequestException:
                    click.echo("Failed to download update")
                    return

                target_filepath = Path(f"guiltysync{release_version}.exe")
                with open(target_filepath, "wb") as exe_file:
                    exe_file.write(dl_res.content)

    def check_or_create_config(self):
        if not self.config_filepath.exists():
            if click.confirm("GuiltySync config was not found. Create one now?"):
                default_config = {
                    "version": str(self.version),
                    "groups": {},
                    "defaults": {},
                }
                self.config_filepath.write_text(
                    json.dumps(default_config), encoding="UTF-8"
                )
            elif not self.prompt_launch():
                click.echo("Quitting...")
                sys.exit(1)

    def check_server(self):
        requests.get(self.server, timeout=3).raise_for_status()

    def create_group(self):
        while True:
            group_name = click.prompt("Enter a group name to join or create a group")
            method = "PUT"
            try:
                requests.get(
                    f"{self.server}/groups/{group_name}", timeout=3
                ).raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    method = "POST"  # Creating a new group
                    if not click.confirm(
                        f"Group '{group_name}' not found. Would you like to create it?"
                    ):
                        continue
                else:
                    raise ServerFailureError(e)
            except requests.exceptions.RequestException as e:
                raise ServerFailureError(e)

            nickname = click.prompt("Enter a nickname for yourself in this group")
            try:
                requests.request(
                    method,
                    f"{self.server}/groups/{group_name}/{nickname if method == 'PUT' else ''}",
                    json={
                        "member": nickname,
                        "mods": {
                            data["id"]: {"name": data["name"], "id": data["id"]}
                            for data in self.mods.values()
                            if data["external"] is False
                        },
                    },
                    timeout=3,
                ).raise_for_status()
            except requests.exceptions.RequestException as e:
                raise ServerFailureError(e)
            break
        self.groups = self.groups | {
            group_name: {"group_name": group_name, "nickname": nickname}
        }

    def get_mod_status(self, mod_id: str, download_id: str) -> dict[str, bool]:
        status = {"have_mod": False, "have_download": False}
        if mod_id in self.mods:
            status["have_mod"] = True
            if download_id == self.mods[mod_id]["chosen_download"]:
                status["have_download"] = True

        return status

    def get_needed_mod_info(self) -> dict:
        needed_mod_info = {"to_update": {}, "to_download": {}}

        for nick, mods in self.group_data.items():
            if nick == self.selected_group["nickname"]:
                continue

            for mod_id, mod_data in mods.items():
                mod_status = self.get_mod_status(mod_id, mod_data["download_id"])
                if mod_status["have_mod"]:
                    if not mod_status["have_download"]:
                        needed_mod_info["to_update"][mod_id] = mod_data
                else:
                    needed_mod_info["to_download"][mod_id] = mod_data

        return needed_mod_info

    def get_or_update_mods(self):
        needed_mod_info = self.get_needed_mod_info()

        for mod_id, mod_data in needed_mod_info["to_update"].items():
            # Have mod locally but with different download ID
            # so need to "update" mod by deleting it first
            # and then add it to the download list
            self.mods[mod_id]["pak"].unlink()
            self.mods[mod_id]["pak"].with_suffix(".id").unlink()
            self.mods[mod_id]["sig"].unlink()
            needed_mod_info["to_download"][mod_id] = mod_data
            click.echo(f"'{mod_data['name']}' will be updated...")

        for mod_id, mod_data in needed_mod_info["to_download"].items():
            click.echo(f"Downloading '{mod_data['name']}'...")
            mod_dir = self.external_dir / Path(mod_data["id"])
            mod_dir.mkdir()

            try:
                guiltysync.download_mod(mod_dir, mod_data)
            except click.ClickException as e:
                click.echo(e)
                click.echo(f"An error occured while downloading '{mod_data['name']}")

        self.scan_mods()

    def print_group_mods(self):
        for nick, mods in self.group_data.items():
            if nick == self.selected_group["nickname"]:
                click.echo(f"{nick} (you):")
            else:
                click.echo(f"{nick}:")

            for mod_data in mods.values():
                mod_status = self.get_mod_status(
                    mod_data["id"], mod_data["download_id"]
                )
                if mod_status["have_mod"]:
                    status_string = "✅[HAVE]"
                    if not mod_status["have_download"]:
                        status_string = "🔄[UPDATE]"
                else:
                    status_string = "🔽[NEED]"
                click.echo(f"\t{status_string} {mod_data['name']}")

    def print_local_shared_mods(self):
        click.echo("Your shared mods:")
        [
            click.echo(f"\t{mod_data['name']}")
            for mod_data in self.mods.values()
            if not mod_data["external"]
        ]

    def prune_external_mods(self):
        local_external_ids_to_delete = {
            mod_id: mod_data
            for mod_id, mod_data in self.mods.items()
            if mod_data["external"]
        }

        for their_mods in self.group_data.values():
            for their_mod_id, their_mod_data in their_mods.items():
                try:
                    # If their_mod_id is found locally and the download_id matches, remove that mod ID from the deletion list
                    if (
                        local_external_ids_to_delete[their_mod_id]["chosen_download"]
                        == their_mod_data["download_id"]
                    ):
                        del local_external_ids_to_delete[their_mod_id]
                    # else the download IDs do not match, so leave the mod ID in the deletion queue
                # A keyError means the mod was not found locally, so it hasn't been downloaded yet
                except KeyError:
                    pass

        for mod_data in local_external_ids_to_delete.values():
            shutil.rmtree(mod_data["parent_dir"])

        self.scan_mods()

    def read_config(self):
        with open(self.config_filepath, "r", encoding="UTF-8") as client_config_file:
            config_data = json.load(client_config_file)

        cur_major = self.version.major

        config_major = versionLib.parse(config_data.get("version", "0.0.0")).major

        if cur_major > config_major:
            if click.confirm(
                "WARNING: your configuration file is for an older version of GuiltySync. Would you like to delete and re-create it now?"
            ):
                self.config_filepath.unlink()
                self.check_or_create_config()
                self.read_config()

        return config_data

    def scan_mods(self):
        mods = defaultdict(dict)

        for file_ in self.shared_dir.glob("**/*"):
            if file_.suffix == ".pak":
                mods[file_.stem]["filename"] = file_.stem
                mods[file_.stem]["parent_dir"] = file_.parent.resolve()
                mods[file_.stem]["external"] = file_.resolve().is_relative_to(
                    self.external_dir
                )
                mods[file_.stem]["pak"] = file_
            elif file_.suffix == ".sig":
                mods[file_.stem]["sig"] = file_
            elif file_.suffix == ".id":
                with open(file_, "r", encoding="UTF-8") as id_file:
                    id_data = json.load(id_file)
                mods[file_.stem]["id"] = id_data["id"]
                mods[file_.stem]["name"] = id_data["name"]
                mods[file_.stem]["chosen_download"] = id_data["chosen_download"]

        invalid_mods = []
        for mod_filename, mod_info in mods.items():
            required_keys = ["pak", "sig"]
            for key in required_keys:
                if not mod_info.get(key):
                    if key == "sig":  # Try to fix missing .sig
                        relative_sig_filepath = mods[mod_filename]["parent_dir"] / Path(
                            f"{mod_filename}.sig"
                        )
                        sig_filepath = self.shared_dir / relative_sig_filepath
                        game_sig_filepath = self.game_filepath / Path(
                            "RED", "Content", "Paks", "pakchunk0-WindowsNoEditor.sig"
                        )
                        shutil.copy(game_sig_filepath, sig_filepath)
                        mod_info["key"] = relative_sig_filepath
                    else:
                        click.echo(
                            f"WARNING: Mod '{mod_filename}' is missing '{key}' file. Skipping mod"
                        )
                        invalid_mods.append(mod_filename)
                        break
        for invalid_mod in invalid_mods:
            del mods[invalid_mod]

        mods_by_id = {}
        for mod_info in mods.values():
            if not mod_info.get("id"):
                while True:
                    click.echo(f"Mod ID not found for '{mod_info['filename']}'")
                    choices = ["Search online", "Enter mod ID manually", "Skip"]
                    choice = helpers.choose_from_list(
                        choices,
                        prompt=f"What would you like to do?",
                    )
                    if choice == choices[0]:
                        try:
                            click.echo(f"Searching online...")
                            online_mod_info = guiltysync.search_for_mod(
                                mod_info["filename"]
                            )
                            online_mod_details = guiltysync.get_mod_details(
                                online_mod_info["_idRow"],
                                online_mod_info["_sModelName"],
                            )
                            mod_info["id"] = str(online_mod_info["_idRow"])
                            mod_info["name"] = online_mod_details["_sName"]
                            mod_info["downloads"] = online_mod_details["_aFiles"]
                            break
                        except guiltysync.ModNotFound:
                            click.echo(f"{mod_info['filename']} not found online")
                    elif choice == choices[1]:
                        entered_id = click.prompt("Enter the mod ID")
                        try:
                            online_mod_details = guiltysync.get_mod_details(entered_id)
                            mod_info["id"] = entered_id
                            mod_info["name"] = online_mod_details["_sName"]
                            mod_info["downloads"] = online_mod_details["_aFiles"]
                            break
                        except guiltysync.ModNotFound:
                            click.echo("Entered ID was not found online")
                    else:
                        click.echo("Skipping mod...")
                        break

            if mod_info.get("id") and not mod_info.get("chosen_download"):
                if len(mod_info["downloads"]) > 1:
                    click.echo("Multiple downloads were found for this mod")
                    choice = helpers.choose_from_list(
                        mod_info["downloads"],
                        display_fn=lambda x: x["_sFile"],
                        prompt="Which one did you download?",
                    )
                    mod_info["chosen_download"] = str(choice["_idRow"])
                else:
                    mod_info["chosen_download"] = str(
                        mod_info["downloads"][0]["_idRow"]
                    )

                with open(
                    mod_info["pak"].with_suffix(".id"),
                    "w",
                    encoding="UTF-8",
                ) as mod_id_file:
                    json.dump(
                        {
                            "id": mod_info["id"],
                            "name": mod_info["name"],
                            "chosen_download": mod_info["chosen_download"],
                        },
                        mod_id_file,
                    )

            mods_by_id[mod_info["id"]] = mod_info

        self.mods = mods_by_id

    def select_group(self):
        if len(self.groups) == 0:
            click.echo("No previous groups found")
            self.create_group()

        if self.selected_group is None:
            create_choice = "Create a new group..."
            while True:
                group = helpers.choose_from_list(
                    list(self.groups.values()),
                    extra_options=[create_choice],
                    display_fn=lambda x: x["group_name"],
                    prompt="Choose a group",
                )
                if group == create_choice:
                    self.create_group()
                    continue
                break

            self.selected_group = group

            if click.confirm(
                "Would you like to use this group automatically from now on? You can change this later by editing the configuration file"
            ):
                self.default_group = group["group_name"]

        self.sync_status_with_group()

    def sync_status_with_group(self):
        self.update_user()

        try:
            group_data_res = requests.get(
                f"{self.server}/groups/{self.selected_group['group_name']}", timeout=3
            )
            group_data_res.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ServerFailureError(e)

        self.group_data = group_data_res.json()

    def update_user(self):
        try:
            requests.put(
                f"{self.server}/groups/{self.selected_group['group_name']}/{self.selected_group['nickname']}",
                json={
                    "member": self.selected_group["nickname"],
                    "mods": {
                        data["id"]: {
                            "name": data["name"],
                            "id": data["id"],
                            "download_id": data["chosen_download"],
                        }
                        for data in self.mods.values()
                        if data["external"] is False
                    },
                },
                timeout=3,
            ).raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ServerFailureError(e)

    def write_config(self):
        with open(self.config_filepath, "w", encoding="UTF-8") as client_config_file:
            json.dump(self.config, client_config_file, indent=2)

    @classmethod
    def launch_game(cls):
        subprocess.run("strive.exe")

    @classmethod
    def prompt_launch(cls, success: bool = False):
        if click.confirm(
            f"Do you want to launch the game{'' if success else ' anyway'}?"
        ):
            cls.launch_game()
            sys.exit(0)
        return False


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        ctx.forward(sync)


@click.option("--game-dir", default=None)
@click.option("--server", default=None)
@click.option("--config", default="guiltysync.json")
@click.option("--version-check/--no-version-check", default=True)
@cli.command()
def sync(config, game_dir, server, version_check):
    try:
        client = SyncClient("2.0.2", Path(config), game_dir, server)

        if version_check:
            client.check_for_update()

        client.select_group()

        client.prune_external_mods()

        client.get_or_update_mods()

        client.print_group_mods()

        options = ["Refresh...", "Launch GGST", "Quit"]
        while True:
            choice = helpers.choose_from_list(options)
            if choice == options[0]:
                click.echo()

                client.scan_mods()  # Must be done in case the user adds mods locally

                client.sync_status_with_group()

                client.prune_external_mods()  # Must be done in case remote users delete mods

                client.get_or_update_mods()

                client.print_group_mods()
            elif choice == options[1]:
                client.launch_game()
                sys.exit(0)
            elif choice == options[2]:
                sys.exit(0)
    except ServerFailureError:
        click.echo("Unable to communicate with sync server")
        try:
            helpers.choose_from_list(
                ["Launch GGST"],
                cancel_prompt="Quit",
                cancellable=True,
            )
        except helpers.ChoiceCancelledException:
            sys.exit(1)
        SyncClient.launch_game()
        sys.exit(0)


cli.add_command(server)


if __name__ == "__main__":
    import sys

    cli(sys.argv[1:])
