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
import shutil

import click
import patoolib
import requests


def get_download_url(mod_id):
    return f"https://gamebanana.com/dl/{mod_id}"


def download_mod(target_dir: Path, mod_id):
    if len(list(target_dir.iterdir())) > 0:
        if click.confirm(f"{target_dir} is not empty. Would you like to empty it? This will delete ALL files in the directory"):
            shutil.rmtree(target_dir)
            target_dir.mkdir()
        else:
            raise click.ClickException(f"'{target_dir}' should be empty")

    download_url = get_download_url(mod_id)
    
    res = requests.get(download_url)
    res.raise_for_status()

    filename = Path(res.request.url.split("/")[-1])
    target_filepath = target_dir / filename

    with open(target_filepath, "wb") as downloaded_file:
        downloaded_file.write(res.content)
    

    patoolib.extract_archive(target_filepath.as_posix(), outdir=target_dir.as_posix(), verbosity=0)

    for file_ in target_dir.glob("**/*"):
        if file_.suffix == ".pak":
            mod_name = file_.stem
            break
    else:
        raise click.ClickException("Unable to find mod .pak in extracted files")

    (target_dir / Path(f"{mod_name}.{mod_id}.id")).touch()
