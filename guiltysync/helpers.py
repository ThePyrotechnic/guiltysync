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
