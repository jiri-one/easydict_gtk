from pathlib import Path
import aiosqlite
import sqlite3
import re
from typing import AsyncIterator, Coroutine, Any
import lzma

# internal imports
from .backend import DBBackend, Result

# TODO: import it from settings, not hardcode it
FILE_DB = Path(__file__).parent.parent / "dict_data/sqlite_eng-cze.db.lzma"


class MimeTypeMismatch(Exception):
    """Thrown when mimetype is mismatch."""

    pass


class SQLiteBackend(DBBackend):
    @staticmethod
    def regexp(expr, item):
        """Helper function for search with regex"""
        reg = re.compile(expr, re.IGNORECASE)
        return reg.search(item) is not None

    def __init__(
        self, file: Path = FILE_DB, table_name="eng_cze", memory_only: bool = True
    ):
        """The main and only one mandatory argument is "file"
        file: for testing purposes it can be uncompressed sqlite db file, but in production it will use lzma compressed db file
        memory_only: everything changed in db will be lost after program end
        """

        self.memory_only = memory_only
        self.table_name = table_name

        # firstly check if file exists
        try:
            if not file.exists():
                raise FileNotFoundError()
        except FileNotFoundError:
            print(f"File {file} not found.")
            exit()

        # check correct mimetype (only suffixes)
        if file.suffixes != [".db", ".lzma"] and file.suffixes != [".db"]:
            raise MimeTypeMismatch(
                "SQLiteBackend can take only SQLite *.db files or *.lzma files, which are LZMA compressed db files."
            )

        self.lzma_compressed = False
        if file.suffixes == [".db", ".lzma"]:
            self.lzma_compressed = True
        self.db_file = file

    async def db_init(self):
        def connect(
            database: Path,
            *,
            iter_chunk_size=64,
            **kwargs: Any,
        ) -> aiosqlite.Connection:
            """Create and return a connection proxy to the sqlite database."""

            def connector() -> sqlite3.Connection:
                sqlite_connection = sqlite3.connect(":memory:", **kwargs)
                self.file_db_bytes = database.read_bytes()
                if self.lzma_compressed:
                    self.file_db_bytes = lzma.decompress(self.file_db_bytes)
                if self.file_db_bytes:  # the db is filled by data
                    sqlite_connection.deserialize(self.file_db_bytes)
                return sqlite_connection

            return aiosqlite.Connection(connector, iter_chunk_size)

        self.conn = await connect(self.db_file)
        await self.conn.create_function("REGEXP", 2, self.regexp)

    async def prepare_db(self):
        """It creates a table in the database.
        A method that is not used in production, because it is not needed for running EasyDict.
        This method was needed when I created dictionary data.
        """

        sql = f"""CREATE TABLE if not exists {self.table_name}
                  (eng TEXT, cze TEXT, notes TEXT,
                   special TEXT, author TEXT)
                """
        await self.conn.execute(sql)

        # save data to memory
        await self.conn.commit()

        if not self.memory_only:
            # save data to the file too
            await self.write_to_file()

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
        await self.conn.executemany(
            f"INSERT INTO {self.table_name} VALUES (?,?,?,?,?)", data
        )
        # save data to memory
        await self.conn.commit()

        if not self.memory_only:
            # save data to the file too
            await self.write_to_file()

    async def search_async(self, word, lang, search_type: str) -> Coroutine | None:
        """Helper coroutine to call search_sorted coroutine - in the future we can add here some logging or stats or something else."""
        return await self.search_sorted(word, lang, search_type)

    async def search_in_db(self, word, lang, search_type: str) -> AsyncIterator[Result]:
        if search_type == "fulltext":
            sql = (
                f"SELECT * FROM {self.table_name} WHERE {lang} LIKE ?",
                [f"%{word}%"],
            )
        elif search_type == "whole_word":
            sql = (
                f"SELECT * FROM {self.table_name} WHERE {lang} REGEXP ?",
                [rf"\b{word}\b"],
            )
        elif search_type == "first_chars":
            sql = (f"SELECT * FROM {self.table_name} WHERE {lang} LIKE ?", [f"{word}%"])
        else:
            raise ValueError("Unknown search_type argument.")

        async with self.conn.execute(*sql) as cursor:
            async for row in cursor:
                yield Result(*row)

    async def write_to_file(self):
        if self.lzma_compressed:
            temp_sqlite_db = sqlite3.connect(":memory:")
            await self.conn.backup(temp_sqlite_db)
            with open(self.db_file, "w+b") as lzma_file:
                lzma_file.write(lzma.compress(temp_sqlite_db.serialize()))
        else:
            async with aiosqlite.connect(self.db_file) as conn_file:
                await self.conn.backup(conn_file)

    async def close_db(self):
        await self.conn.close()
