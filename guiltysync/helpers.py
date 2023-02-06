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
from collections.abc import Callable, Iterable

import click


class ChoiceCancelledException(Exception):
    pass


def print_iterable(i: Iterable, *, display_fn: Callable | None = None):
    for index, item in enumerate(i, 1):
        click.echo(f"{index}:\t {display_fn(item) if display_fn is not None else item}")


def choose_from_list(
    s: list,
    *,
    extra_options: list | None = None,
    display_fn: Callable | None = None,
    prompt: str = "Choose an option",
    cancellable: bool = False,
    cancel_prompt: str = "Cancel...",
):
    if extra_options is None:
        extra_options = []

    final_seq = s

    if display_fn is not None:
        final_seq = [display_fn(item) for item in s]

    # Cannot append because that will modify the input sequence
    # yes, this function is O(n^3)
    final_seq = (
        final_seq + extra_options + [cancel_prompt]
        if cancellable
        else final_seq + extra_options
    )

    print_iterable(final_seq)

    while True:
        choice = click.prompt(prompt, type=int)
        try:
            if cancellable and choice == len(final_seq):
                raise ChoiceCancelledException
            elif choice <= len(s):
                return s[choice - 1]
            else:
                return final_seq[choice - 1]
        except KeyError:
            click.echo("Invalid choice")
            pass
