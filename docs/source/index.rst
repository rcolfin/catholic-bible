catholic-bible
==============

Welcome to the catholic-bible documentation! Here you will find links to the core modules and examples of how to use each.


Provides an API for scraping the `Bible <https://bible.usccb.org/bible/>`_ website of United States Conference of Catholic Bishops.

Modules
-------

If there is functionality that is missing or an error in the docs, please open a new issue `here <https://github
.com/rcolfin/catholic-bible/issues>`_.

.. toctree::
    :maxdepth: 1

    browser
    catholic_bible/challenge
    catholic_bible/constants
    catholic_bible/models
    catholic_bible/usccb

Install
-------

To install catholic-bible from PyPI, use the following command:

    $ pip install catholic-bible

You can also clone the repo and run the following command in the project root to install the source code as editable:

    $ pip install -e .

The site sometimes requires a browser to pass a JavaScript challenge. Browser support is optional; to enable it,
install the ``browser`` extra (see :doc:`browser` for configuration and Docker usage):

    $ pip install 'catholic-bible[browser]'

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Examples
--------

The following example fetches a chapter:

.. code-block:: python

    import asyncio

    from catholic_bible import USCCB

    async def main() -> None:
        async with USCCB() as usccb:
            chapter = await usccb.get_chapter("genesis", 1)
            if chapter:
                print(chapter.title)
                for section in chapter.sections:
                    for verse in section.verses:
                        print(verse)

    asyncio.run(main())

The following example fetches a single verse:

.. code-block:: python

    async with USCCB() as usccb:
        verse = await usccb.get_verse("john", 3, 16)
        if verse:
            print(verse.text)

The following example fetches all chapters of a book, in Spanish:

.. code-block:: python

    from catholic_bible import models

    async with USCCB() as usccb:
        chapters = await usccb.get_book("psalms", language=models.Language.SPANISH)
        for chapter in chapters:
            print(chapter.title)

As a CLI:

.. code-block:: bash

    # List all 73 books
    python -m catholic_bible list-books

    # Fetch a chapter and print it
    python -m catholic_bible get-chapter --book genesis --chapter 1

    # Fetch a chapter and save it to JSON
    python -m catholic_bible get-chapter --book genesis --chapter 1 --save genesis-1.json

    # Fetch a single verse
    python -m catholic_bible get-verse --book john --chapter 3 --verse 16

    # Fetch an entire book
    python -m catholic_bible get-book --book psalms
