import pytest
from src.edge_case_handler import handle_edge_case_x

@pytest.mark.asyncio
async def test_handle_edge_case_x_not_implemented():
    with pytest.raises(NotImplementedError) as exc_info:
        await handle_edge_case_x()
    assert "REQ-456 not yet implemented" in str(exc_info.value)