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
import json
from pathlib import Path
import shutil

import click
import patoolib
import requests

import guiltysync.helpers as helpers


class ModNotFound(Exception):
    pass


def get_mod_details(mod_id, mod_category=None):
    if mod_category is None:
        mod_category = (
            "Sound"
            if click.confirm(
                "Is this a music / sound mod? (if it changes anything other than audio, answer no)"
            )
            else "Mod"
        )

    try:
        res = requests.get(
            f"https://gamebanana.com/apiv10/{mod_category}/{mod_id}/ProfilePage",
            timeout=3,
        )
        res.raise_for_status()
    except (requests.exceptions.HTTPError, requests.exceptions.Timeout):
        raise ModNotFound()

    return res.json()


def search_for_mod(search_string, mod_category=None):
    if mod_category is None:
        mod_category = (
            "Sound"
            if click.confirm(
                "Is this a music / sound mod? (if it changes anything other than audio, answer no)"
            )
            else "Mod"
        )

    while True:
        try:
            params = {
                "_nPage": 1,
                "_nPerPage": 10,
                "_sModelName": mod_category,
                "sOrder": "best_match",
                "idGameRow": "11534",
                "_sSearchString": search_string,
                "_csvFields": "name,owner",
            }
            click.echo(f"Search results for '{search_string}'")
            try:
                res = requests.get(
                    "https://gamebanana.com/apiv10/Util/Search/Results",
                    params=params,
                    timeout=3,
                ).json()
            except (requests.exceptions.HTTPError, requests.exceptions.Timeout):
                raise ModNotFound()

            return helpers.choose_from_list(
                res["_aRecords"],
                display_fn=lambda x: x["_sName"],
                prompt="Choose a mod",
                cancellable=True,
                cancel_prompt="Mod not listed...",
            )
        except helpers.ChoiceCancelledException:
            try:
                helpers.choose_from_list(
                    ["Change the search term"],
                    cancel_prompt="Cancel online search...",
                    cancellable=True,
                )
                search_string = click.prompt("Enter a new search term")
            except helpers.ChoiceCancelledException:
                raise ModNotFound()


def download_mod(target_dir: Path, mod_data):
    if len(list(target_dir.iterdir())) > 0:
        if click.confirm(
            f"{target_dir} is not empty. Would you like to empty it? This will delete ALL files in the directory"
        ):
            shutil.rmtree(target_dir)
            target_dir.mkdir()
        else:
            raise click.ClickException(f"'{target_dir}' should be empty")

    download_url = f"https://gamebanana.com/dl/{mod_data['download_id']}"

    res = requests.get(download_url, timeout=3)
    res.raise_for_status()

    assert res.request.url is not None
    filename = Path(res.request.url.split("/")[-1])
    target_filepath = target_dir / filename

    with open(target_filepath, "wb") as downloaded_file:
        downloaded_file.write(res.content)

    patoolib.extract_archive(
        target_filepath.as_posix(), outdir=target_dir.as_posix(), verbosity=0
    )

    for file_ in target_dir.glob("**/*"):
        if file_.suffix == ".pak":
            mod_filename = file_.stem
            break
    else:
        raise click.ClickException("Unable to find mod .pak in extracted files")

    with open(
        target_dir / Path(f"{mod_filename}.id"), "w", encoding="UTF-8"
    ) as mod_id_file:
        json.dump(
            {
                "id": mod_data["id"],
                "name": mod_data["name"],
                "chosen_download": mod_data["download_id"],
            },
            mod_id_file,
        )

    target_filepath.unlink()
