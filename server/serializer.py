import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from config import GAME_CONFIG


class GameResultSerializer:
    def __init__(self):
        self.results_dir = GAME_CONFIG["RESULTS_DIR"]
        self.results_dir.mkdir(exist_ok=True)

    def serialize(self, game_data: Dict[str, Any]) -> str:
        root = ET.Element("CodeMasterRound")

        # Основная информация
        ET.SubElement(root, "StartTime").text = game_data["start_time"].isoformat()
        ET.SubElement(root, "EndTime").text = game_data["end_time"].isoformat()
        ET.SubElement(root, "SecretCode").text = game_data["code"]
        ET.SubElement(root, "Winner").text = game_data["winner"] or "None"

        players_elem = ET.SubElement(root, "Players")
        for player, attempts in game_data["attempts"].items():
            player_elem = ET.SubElement(players_elem, "Player", name=player)
            player_elem.set("attempts", str(len(attempts)))

            for i, (guess, black, white) in enumerate(attempts, 1):
                attempt_elem = ET.SubElement(player_elem, "Attempt", number=str(i))
                ET.SubElement(attempt_elem, "Guess").text = guess
                ET.SubElement(attempt_elem, "BlackMarkers").text = str(black)
                ET.SubElement(attempt_elem, "WhiteMarkers").text = str(white)

        timestamp = game_data["start_time"].strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"round_{timestamp}.xml"

        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

        return str(filename)