from io import BytesIO

import pytest

from repono import FileItem
from repono.exceptions import FileExtensionNotAllowed
from repono.filters import ValidateExtension


@pytest.fixture
def item():
    return FileItem(filename="file.txt", path=("folder",), data=BytesIO(b"content"))


def test_valid_extension(item):
    filter = ValidateExtension(extensions=["txt", "html"])

    result = filter._apply(item)

    # Verify that the item is unchanged
    assert item == result


def test_invalid_extension(item):
    filter = ValidateExtension(extensions=["png", "jpg"])

    with pytest.raises(FileExtensionNotAllowed):
        filter._apply(item)
