"""Generic page-walker for fetch backends.

Centralises the ``while True: fetch -> persist-cursor -> yield`` loop that
each backend re-implemented. Owns:

- the search-error swallow (log + return on transient API failure),
- the empty-results terminator,
- the "persist next cursor *before* yielding" invariant that keeps
  cap-hit-mid-page resumable, and
- the ``dry_run`` gate that no-ops cursor persistence.
"""

from __future__ import annotations

import logging
from typing import Callable, Iterator, TypeVar

from ._download import Candidate

CursorT = TypeVar("CursorT")
PageT = TypeVar("PageT")


def paginate(
    *,
    fetch_page: Callable[[CursorT], PageT],
    advance: Callable[[CursorT, PageT], "tuple[CursorT, bool] | None"],
    extract: Callable[[PageT], Iterator[Candidate]],
    get_cursor: Callable[[], CursorT],
    set_cursor: Callable[[CursorT], None],
    logger: logging.Logger,
    search_errors: tuple[type[BaseException], ...],
    dry_run: bool = False,
) -> Iterator[Candidate]:
    """Walk pages, yielding ``Candidate`` until ``advance`` reports done.

    ``fetch_page(cursor)`` returns the page object and may raise any of
    ``search_errors`` (logged + treated as terminal).

    ``advance(cursor, page)`` returns ``(next_cursor, done)`` — ``next_cursor``
    is what to persist; ``done`` is ``True`` when iteration should stop after
    yielding the current page. Returning ``None`` is an immediate hard-stop
    (e.g. catalog-level error reported in the page payload) — no cursor
    mutation, no yields.
    """
    cursor = get_cursor()
    while True:
        try:
            page = fetch_page(cursor)
        except search_errors as exc:
            logger.error(f"page request failed at cursor={cursor!r}: {exc!r}; stopping")
            return
        result = advance(cursor, page)
        if result is None:
            return
        next_cursor, done = result
        if not dry_run:
            set_cursor(next_cursor)
        yield from extract(page)
        if done:
            return
        cursor = next_cursor
