class DestinationResearchProvider:
    """Provides destination research, POIs, attractions, and cultural insights."""

    @staticmethod
    def get_recommendations(
        destination: str = "Tokyo",
        interests: list[str] | None = None,
        pace: str = "balanced",
    ) -> list[dict]:
        interests = interests or []
        dest_lower = destination.lower()

        if "tokyo" in dest_lower:
            return [
                {
                    "name": "Senso-ji Temple & Nakamise Shopping Street",
                    "category": "culture",
                    "description": "Tokyo's oldest and most significant ancient Buddhist temple with vibrant traditional craft and snack stalls.",
                    "location": "Asakusa, Tokyo",
                    "estimated_cost": 0.0,
                    "opening_hours": "06:00 - 17:00",
                    "source_url": "https://www.trip.com/travel-guide/attraction/tokyo/senso-ji-10524185/",
                },
                {
                    "name": "Tsukiji Outer Market Gourmet Food Tour",
                    "category": "food",
                    "description": "Lively street food market serving fresh sashimi, tamagoyaki, wagyu skewers, and matcha sweets.",
                    "location": "Tsukiji, Tokyo",
                    "estimated_cost": 25.0,
                    "opening_hours": "08:00 - 14:00",
                    "source_url": "https://www.trip.com/travel-guide/attraction/tokyo/tsukiji-outer-market-90059/",
                },
                {
                    "name": "Shibuya Sky Observation Deck",
                    "category": "sightseeing",
                    "description": "360-degree open-air rooftop observation deck overlooking Shibuya Crossing and Mount Fuji.",
                    "location": "Shibuya Scramble Square, Tokyo",
                    "estimated_cost": 20.0,
                    "opening_hours": "10:00 - 22:30",
                    "source_url": "https://www.trip.com/travel-guide/attraction/tokyo/shibuya-sky-57753907/",
                },
                {
                    "name": "teamLab Planets TOKYO Digital Art Museum",
                    "category": "entertainment",
                    "description": "Immersive digital art museum where visitors walk through water and interactive projection environments.",
                    "location": "Toyosu, Tokyo",
                    "estimated_cost": 32.0,
                    "opening_hours": "09:00 - 22:00",
                    "source_url": "https://www.trip.com/travel-guide/attraction/tokyo/teamlab-planets-tokyo-24603954/",
                },
            ]

        # Generic destination fallback
        return [
            {
                "name": f"{destination} Historic Old Town",
                "category": "culture",
                "description": f"Historic landmark and architectural walking tour in the heart of {destination}.",
                "location": f"Old Quarter, {destination}",
                "estimated_cost": 0.0,
                "opening_hours": "Open 24 hours",
                "source_url": f"https://www.trip.com/travel-guide/{destination}",
            },
            {
                "name": f"{destination} Central Food Market",
                "category": "food",
                "description": f"Famous local market showcasing the best authentic cuisine and specialties of {destination}.",
                "location": f"Downtown {destination}",
                "estimated_cost": 15.0,
                "opening_hours": "09:00 - 18:00",
                "source_url": f"https://www.trip.com/travel-guide/{destination}",
            },
            {
                "name": f"{destination} Scenic City Viewpoint",
                "category": "sightseeing",
                "description": f"Popular panorama point offering breathtaking views across {destination}.",
                "location": f"Hilltop District, {destination}",
                "estimated_cost": 10.0,
                "opening_hours": "08:00 - 20:00",
                "source_url": f"https://www.trip.com/travel-guide/{destination}",
            },
        ]
