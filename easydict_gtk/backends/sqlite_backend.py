from pathlib import Path
import aiosqlite
import re
from typing import AsyncIterator, Coroutine

# internal imports
from .backend import DBBackend, Result

# TODO: import it from settings, not hardcode it
FILE_DB = Path(__file__).parent.parent / "dict_data/sqlite_eng-cze.db"


class SQLiteBackend(DBBackend):
    @staticmethod
    def regexp(expr, item):
        """Helper function for search with regex"""
        reg = re.compile(expr, re.IGNORECASE)
        return reg.search(item) is not None

    def __init__(self, file=FILE_DB):
        try:
            self.db_file = file
            if not self.db_file.exists():
                raise FileNotFoundError()
        except FileNotFoundError:
            print(f"DB file {self.db_file} not found.")
            exit()

    async def db_init(self, memory=True):
        if memory:
            self.conn = await aiosqlite.connect(":memory:")
            async with aiosqlite.connect(self.db_file) as conn_file:
                await conn_file.backup(self.conn)
        else:
            self.conn = await aiosqlite.connect(self.db_file)
        await self.conn.create_function("REGEXP", 2, self.regexp)

    async def prepare_db(self, db_name: str):
        """It creates a table in the database.
        A method that is not (yet) used in production."""
        sql = f"""CREATE TABLE if not exists {db_name}
                  (eng TEXT, cze TEXT, notes TEXT,
                   special TEXT, author TEXT)
                """
        await self.conn.execute(sql)
        await self.conn.commit()

    async def fill_db(self, raw_file: Path = None):
        """Filling the database with data.
        A method that is not (yet) used in production."""
        if not raw_file:
            raw_file = Path(__file__).parent.parent / "data/en-cs.txt"
        if not raw_file.exists():
            raise FileNotFoundError()

        data = []
        with open(raw_file) as file:
            for line in file:
                line_list = line.split("\t")
                data.append(
                    (
                        line_list[0],
                        line_list[1],
                        line_list[2],
                        line_list[3],
                        str(line_list[4]).replace(
                            "\n", ""
                        ),  # sometimes there are some unnecessary new lines
                    )
                )
        await self.conn.executemany("INSERT INTO eng_cze VALUES (?,?,?,?,?)", data)
        # save data
        await self.conn.commit()

    async def search_async(self, word, lang, search_type: str) -> Coroutine | None:
        """Helper coroutine to call search_sorted coroutine - in the future we can add here some logging or stats or something else."""
        return await self.search_sorted(word, lang, search_type)

    async def search_in_db(self, word, lang, search_type: str) -> AsyncIterator[Result]:
        if search_type == "fulltext":
            sql = (f"SELECT * FROM eng_cze WHERE {lang} LIKE ?", [f"%{word}%"])
        elif search_type == "whole_word":
            sql = (f"SELECT * FROM eng_cze WHERE {lang} REGEXP ?", [rf"\b{word}\b"])
        elif search_type == "first_chars":
            sql = (f"SELECT * FROM eng_cze WHERE {lang} LIKE ?", [f"{word}%"])
        else:
            raise ValueError("Unknown search_type argument.")

        async with self.conn.execute(*sql) as cursor:
            async for row in cursor:
                yield Result(*row)
