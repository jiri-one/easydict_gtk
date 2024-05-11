import pytest
import pytest_asyncio
import lzma
from pathlib import Path

# internal imports
from easydict_gtk.backends.sqlite_backend import SQLiteBackend
from easydict_gtk.backends.backend import Result

# type anotations
empty_adb: SQLiteBackend


@pytest.fixture
def dummy_data():
    return """
test_eng	test_cze	note	special	author
eng	cze	note	special	author
english	czech	notes	specials	authors
    """.strip()


#
# helper functions and coroutines
#
def lzma_file(tmp_path: Path):
    "Create compressed empty file"
    file_db = tmp_path / "test.db"
    file_db.touch()
    lzma_db_file = tmp_path / "test.db.lzma"
    with lzma.open(lzma_db_file, "w") as f:
        f.write(file_db.read_bytes())
    return lzma_db_file


def db_file(tmp_path: Path):
    file_db = tmp_path / "test.db"
    file_db.touch()
    return file_db


async def search_word_and_close_db(async_db):
    """Helper function which search word only and check, if there is a correct result."""
    async for result in async_db.search_in_db(
        word="english", lang="eng", search_type="whole_word"
    ):
        return result.cze


#
# fixtures
#
@pytest.fixture
def raw_file(tmp_path: Path, dummy_data):
    file = tmp_path / "raw_file.txt"
    file.write_text(dummy_data)
    return file


@pytest_asyncio.fixture(params=[db_file, lzma_file])
async def adb(tmp_path, request: pytest.FixtureRequest):
    file = request.param(tmp_path)
    async_db = SQLiteBackend(file)
    await async_db.db_init()
    try:
        yield async_db
    finally:
        await async_db.conn.close()


# TESTS
async def test_prepare_db(adb):
    table_name = "test"
    adb.table_name = table_name
    sql = (
        f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        [f"{table_name}"],
    )

    async with adb.conn.execute(*sql) as cursor:
        results = await cursor.fetchall()  # result format is here [(0,)]
        assert results[0][0] == 0  # should find 0 match, table wasn't created yet

    await adb.prepare_db()  # create table

    async with adb.conn.execute(*sql) as cursor:
        results = await cursor.fetchall()
        assert results[0][0] == 1  # should find 1 match

    async with adb.conn.execute("SELECT name FROM sqlite_master") as cursor:
        result = await cursor.fetchone()
        assert result == (table_name,)  # should find our new table with table_name


async def test_fill_db(adb, raw_file, dummy_data):
    await adb.prepare_db()  # create table
    await adb.fill_db(raw_file)  # fill table with dummy data from dummy file
    sql = "SELECT * FROM eng_cze"  # get all data from table
    dummy_data = dummy_data.split("\n")  # split dummy data by new line
    dummy_data = [
        tuple(row.split("\t")) for row in dummy_data
    ]  # every line is now tuple; originally each element was separated by a tab
    async with adb.conn.execute(sql) as cursor:
        index = 0
        async for row in cursor:  # one row is tuple of columns
            assert row == dummy_data[index]
            index += 1


async def test_search_in_db(adb, raw_file):
    await adb.prepare_db()  # create table

    search = adb.search_in_db(word="test", lang="eng", search_type="fulltext")
    async for x in search:
        assert False  # this will never run if no results are found

    await adb.fill_db(raw_file)  # fill table with dummy data from dummy file
    # and try search again
    async for result in adb.search_in_db(
        word="test", lang="eng", search_type="fulltext"
    ):
        assert result  # this time we should have some results
        assert isinstance(result, Result)  # and result should be correct type


async def test_search_in_db_with_all_search_types(adb, raw_file):
    await adb.prepare_db()  # create table
    await adb.fill_db(raw_file)  # fill table with dummy data from dummy file
    # test fulltext search
    async for result in adb.search_in_db(
        word="test", lang="eng", search_type="fulltext"
    ):
        assert result.eng == "test_eng"
    # test first_chars search
    async for result in adb.search_in_db(
        word="eng", lang="eng", search_type="first_chars"
    ):
        assert "eng" in result.eng
    # test whole_word search
    async for result in adb.search_in_db(
        word="english", lang="eng", search_type="whole_word"
    ):
        assert result.eng == "english"
    # test bad type of search_type parameter
    with pytest.raises(ValueError, match="Unknown search_type argument."):
        async for result in adb.search_in_db(
            word="ehm", lang="eng", search_type="unknown"
        ):
            assert False  # this will never run if no results are found


@pytest.mark.parametrize(argnames="lzma_or_db_file", argvalues=[db_file, lzma_file])
async def test_with_real_db_file(tmp_path, raw_file, lzma_or_db_file):
    """All other tests are with SQLiteBackend(file, memory_only=True), so they are operating only with memory, but this test is with argument memory_only=False, so we need to test, if changes are propagated to file itself.
    This test is invoked two times: with uncompressed db_file and with lzma compressed file.
    """

    file_db = lzma_or_db_file(tmp_path)  # create empty file
    async_db = SQLiteBackend(file_db, memory_only=False)
    await async_db.db_init()
    await async_db.prepare_db()  # create empty table
    assert file_db.read_bytes()  # file_db is not empty
    file_db_bytes = file_db.read_bytes()  # bytes after prepare_db()
    assert not await search_word_and_close_db(async_db)  # no results
    await async_db.fill_db(raw_file)  # fill table with dummy data from dummy file

    assert file_db_bytes != file_db.read_bytes()  # check iw fill_db() modified db_file

    # test whole_word search on filled memory
    assert "czech" == await search_word_and_close_db(async_db)
    await async_db.conn.close()  # close the db connection
    del async_db

    # read again the db_file and try search again, the data should be permanent
    async_db = SQLiteBackend(file_db)
    await async_db.db_init()
    assert "czech" == await search_word_and_close_db(async_db)
    await async_db.conn.close()
