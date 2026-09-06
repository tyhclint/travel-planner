from pydantic import BaseModel, ConfigDict, Field


class KiwiBaggageOutput(BaseModel):
    """Included per-traveler baggage counts from Kiwi search results."""

    personalItem: int = 0
    cabinBag: int = 0
    checkedBag: int = 0


class KiwiPassengersOutput(BaseModel):
    """Passenger counts returned by Kiwi for a search."""

    adults: int = 0
    children: int = 0
    infants: int = 0


class KiwiSegmentOutput(BaseModel):
    """One carrier-operated segment inside a Kiwi flight leg."""

    model_config = ConfigDict(extra="allow")

    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    fromCity: str | None = None
    toCity: str | None = None
    fromName: str | None = None
    toName: str | None = None
    fromCountry: str | None = None
    toCountry: str | None = None
    departureTime: str | None = None
    arrivalTime: str | None = None
    durationSeconds: int | None = None
    carrier: str | None = None
    carrierName: str | None = None
    flightNumber: str | None = None
    cabinClass: str | None = None


class KiwiLegOutput(BaseModel):
    """Outbound or inbound leg returned by Kiwi."""

    model_config = ConfigDict(extra="allow")

    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    departureTime: str | None = None
    arrivalTime: str | None = None
    durationSeconds: int | None = None
    stops: int | None = None
    route: list[str] = Field(default_factory=list)
    cabinClass: str | None = None
    segments: list[KiwiSegmentOutput] = Field(default_factory=list)


class KiwiItineraryOutput(BaseModel):
    """One itinerary returned by Kiwi search-flight."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    price: float | None = None
    priceFormatted: str | None = None
    totalDurationSeconds: int | None = None
    bookingUrl: str | None = None
    imageId: str | None = None
    baggage: KiwiBaggageOutput | None = None
    outbound: KiwiLegOutput | None = None
    inbound: KiwiLegOutput | None = None


class KiwiSearchFlightsOutput(BaseModel):
    """Structured output declared by the Kiwi MCP search-flight tool."""

    model_config = ConfigDict(extra="allow")

    query: str
    currency: str | None = None
    passengers: KiwiPassengersOutput | None = None
    resultsCount: int = 0
    itineraries: list[KiwiItineraryOutput] = Field(default_factory=list)
    searchTimeMs: int = 0
    error: str | None = None
