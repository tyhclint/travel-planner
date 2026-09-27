class MoodTripAccommodationError(RuntimeError):
    """Base error for MoodTrip accommodation provider integration failures."""


class MoodTripPayloadValidationError(MoodTripAccommodationError):
    """Raised when MoodTrip returns payload data that does not match the expected shape."""
