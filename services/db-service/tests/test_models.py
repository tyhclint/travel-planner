from app.models.bookmark_document import BookmarkDocument
from app.models.conversation_document import ConversationDocument
from app.models.trip_document import TripDocument


def test_trip_document_creation():
    trip = TripDocument(
        title="5 Days in Tokyo",
        destination="Tokyo",
        origin="Singapore",
        trip_length_days=5,
    )
    assert trip.destination == "Tokyo"
    assert trip.trip_length_days == 5
    assert trip.status == "draft"
    assert trip.id is not None


def test_conversation_document_creation():
    conv = ConversationDocument(
        _id="thread-user-456",
        messages=[{"role": "user", "content": "Plan a trip"}],
    )
    assert conv.thread_id == "thread-user-456"
    assert len(conv.messages) == 1


def test_bookmark_document_creation():
    bookmark = BookmarkDocument(
        user_id="user-123",
        item_type="flight",
        item_data={"airline": "Singapore Airlines", "price": 500},
    )
    assert bookmark.user_id == "user-123"
    assert bookmark.item_type == "flight"
    assert bookmark.item_data["price"] == 500
