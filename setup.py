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
from setuptools import setup, find_packages


setup(
    name="guiltysync",
    version="2.0.3",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["Click", "requests", "fastapi", "uvicorn", "patool", "packaging"],
    extras_require={"exe": ["pyinstaller"], "dev": ["black"]},
    entry_points={
        "console_scripts": [
            "guiltysync = guiltysync.cli:cli",
        ],
    },
)
