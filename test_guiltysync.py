
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
from pathlib import Path

from click.testing import CliRunner
import requests

from guiltysync.scripts import cli


GAME_DIR = "/mnt/storage/SteamLibrary/steamapps/common/GUILTY GEAR STRIVE/"
SERVER = "http://localhost:5000"


def rm_config():
    config_file = Path("guiltysync.json")
    config_file.unlink(missing_ok=True)


def delete_groups():
    res = requests.delete(f"{SERVER}/groups")
    res.raise_for_status()


def delete_group(group, allow_404=True):
    res = requests.delete(f"{SERVER}/groups/{group}")
    try:
        res.raise_for_status()
    except requests.HTTPError as e:
        if not e.response.status_code == 404 or not allow_404:
            raise e


def test_new_group():
    delete_group("test")
    rm_config()

    runner = CliRunner()
    result = runner.invoke(cli,
        [
            "sync",
            "--game-dir",
            GAME_DIR,
            "--server",
            SERVER
        ],
        input = "\n".join(
            [
                "y",
                "test",
                "mike",
                "3"
            ]
        )
    )
    print(result.stdout)
    assert result.exit_code == 0


def test_existing_group():
    test_new_group()

    runner = CliRunner()
    result = runner.invoke(cli,
        [
            "sync",
            "--game-dir",
            GAME_DIR,
            "--server",
            SERVER
        ],
        input = "\n".join(
            [
                "1"
            ]
        )
    )
    assert result.exit_code == 0


def test_new_user_with_existing_group():
    delete_group("test2")
    rm_config()
    
    test_new_group()

    runner = CliRunner()
    result = runner.invoke(cli,
        [
            "sync",
            "--game-dir",
            GAME_DIR,
            "--server",
            SERVER
        ],
        input = "\n".join(
            [
                "2",
                "test2",
                "mike"
            ]
        )
    )
    assert result.exit_code == 0


def test_new_local_group_exists_on_remote():
    delete_group("test")
    test_new_group()
    rm_config()

    runner = CliRunner()
    result = runner.invoke(cli,
        [
            "sync",
            "--game-dir",
            GAME_DIR,
            "--server",
            SERVER
        ],
        input = "\n".join(
            [
                "y",
                "test",
                "mike"
            ]
        )
    )
    assert result.exit_code == 0


def test_add_same_group_twice():
    delete_group("test")
    test_new_group()

    runner = CliRunner()
    result = runner.invoke(cli,
        [
            "sync",
            "--game-dir",
            GAME_DIR,
            "--server",
            SERVER
        ],
        input = "\n".join(
            [
                "2",
                "test",
                "mike"
            ]
        )
    )
    
    result = runner.invoke(cli,
        [
            "sync",
            "--game-dir",
            GAME_DIR,
            "--server",
            SERVER
        ],
        input = "\n".join(
            [
                "2",
                "test",
                "mike"
            ]
        )
    )
    assert result.exit_code == 0


def test_multiple_users():
    delete_groups()
    test_new_group()

    requests.put(f"{SERVER}/groups/test/steve", json=
        {
            "member": "steve",
            "mods": {
                "903027": {
                    "name": "Strapped Jack-O Thigh Highs",
                    "id": "903027"
                },
                "654361": {
                    "name": "Maskless Jack-O v1.2",
                    "id": "654361"
                }
            }
        }
    )


if __name__ == "__main__":
    # test_new_group()
    # test_existing_group()
    # test_new_user_with_existing_group()
    # test_new_local_group_exists_on_remote()
    # test_add_same_group_twice()
    test_multiple_users()
